"""Compatibility scoring, matching and explanations.

A pair is good when each can help the other (strong where the other is weak), when their free time
overlaps, and when their study style and goal agree. Matching maximises the total score of all pairs,
using a greedy start followed by pairwise-swap improvement. With an odd cohort the last student joins
the best pair as a trio.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import combinations

HELP_THRESHOLD = 4  # "strong" skill level (0-5)
WEAK_THRESHOLD = 2  # "needs help" level
W_HELP, W_TIME, W_STYLE, W_GOAL = 5.0, 3.0, 1.5, 1.0
MAX_SHARED = 6  # more than this many shared slots adds nothing


class BuddyError(ValueError):
    """Bad input; message is safe to show."""


@dataclass(frozen=True)
class Student:
    name: str
    skills: dict[str, int]
    slots: tuple[str, ...]
    style: str = "quiet"
    goal: str = "exam"


@dataclass
class PairInfo:
    members: list[str]
    score: float
    helps: list[str]  # "Ana helps Ben with Calculus"
    shared_slots: list[str]
    reasons: list[str]


@dataclass
class Result:
    pairs: list[PairInfo]
    total_score: float
    random_baseline: float
    blocking_pairs: int
    unmatched_slots_warning: list[str] = field(default_factory=list)


def validate(students: list[Student]) -> None:
    if len(students) < 2:
        raise BuddyError("need at least two students")
    names = [s.name for s in students]
    if len(set(names)) != len(names):
        raise BuddyError("student names must be unique")
    for s in students:
        if any(not 0 <= v <= 5 for v in s.skills.values()):
            raise BuddyError(f"{s.name}: skill levels must be between 0 and 5")


def helps(a: Student, b: Student) -> list[tuple[str, int]]:
    """Subjects where `a` is strong and `b` needs help, with the size of the gap."""
    out = []
    for subject, level in a.skills.items():
        if level >= HELP_THRESHOLD and b.skills.get(subject, 5) <= WEAK_THRESHOLD:
            out.append((subject, level - b.skills[subject]))
    return out


def shared_slots(a: Student, b: Student) -> list[str]:
    return sorted(set(a.slots) & set(b.slots))


def pair_score(a: Student, b: Student) -> float:
    """Symmetric compatibility in [0, ~10]."""
    gap = sum(g for _, g in helps(a, b)) + sum(g for _, g in helps(b, a))
    help_part = min(gap, 10) / 10
    time_part = min(len(shared_slots(a, b)), MAX_SHARED) / MAX_SHARED
    style_part = 1.0 if a.style == b.style else 0.0
    goal_part = 1.0 if a.goal == b.goal else 0.0
    return round(W_HELP * help_part + W_TIME * time_part + W_STYLE * style_part + W_GOAL * goal_part, 3)


def _total(pairs: list[tuple[int, int]], scores: list[list[float]]) -> float:
    return sum(scores[i][j] for i, j in pairs)


def _greedy(n: int, scores: list[list[float]], rng: random.Random) -> list[tuple[int, int]]:
    order = list(combinations(range(n), 2))
    rng.shuffle(order)
    order.sort(key=lambda p: -scores[p[0]][p[1]])
    used: set[int] = set()
    pairs = []
    for i, j in order:
        if i not in used and j not in used:
            pairs.append((i, j))
            used |= {i, j}
    return pairs


def _improve(pairs: list[tuple[int, int]], scores: list[list[float]]) -> list[tuple[int, int]]:
    """2-opt on pairs: for two pairs (a,b),(c,d) try (a,c),(b,d) and (a,d),(b,c)."""
    pairs = list(pairs)
    improved = True
    while improved:
        improved = False
        for x, y in combinations(range(len(pairs)), 2):
            (a, b), (c, d) = pairs[x], pairs[y]
            current = scores[a][b] + scores[c][d]
            for new in (((a, c), (b, d)), ((a, d), (b, c))):
                total = scores[new[0][0]][new[0][1]] + scores[new[1][0]][new[1][1]]
                if total > current + 1e-9:
                    pairs[x], pairs[y] = new
                    improved = True
                    break
    return pairs


def count_blocking(pairs: list[tuple[int, int]], scores: list[list[float]], n: int) -> int:
    """Pairs of students who would both rather be together than with their assigned partner."""
    partner = {}
    for i, j in pairs:
        partner[i], partner[j] = j, i
    blocking = 0
    for i, j in combinations(range(n), 2):
        if partner.get(i) == j:
            continue
        pi, pj = partner.get(i), partner.get(j)
        better_i = pi is None or scores[i][j] > scores[i][pi] + 1e-9
        better_j = pj is None or scores[i][j] > scores[j][pj] + 1e-9
        blocking += int(better_i and better_j)
    return blocking


def explain(a: Student, b: Student) -> PairInfo:
    h = [f"{a.name} can help {b.name} with {s}" for s, _ in helps(a, b)] + [
        f"{b.name} can help {a.name} with {s}" for s, _ in helps(b, a)
    ]
    shared = shared_slots(a, b)
    reasons = list(h)
    if shared:
        reasons.append(f"{len(shared)} shared free slot(s), e.g. {shared[0]}")
    else:
        reasons.append("no shared free slot yet: agree a new time")
    if a.style == b.style:
        reasons.append(f"both prefer {a.style} sessions")
    if a.goal == b.goal:
        reasons.append(f"both are studying for {'an exam' if a.goal == 'exam' else 'the long run'}")
    return PairInfo([a.name, b.name], pair_score(a, b), h, shared, reasons)


def match(students: list[Student], seed: int = 0) -> Result:
    validate(students)
    n = len(students)
    scores = [[0.0] * n for _ in range(n)]
    for i, j in combinations(range(n), 2):
        scores[i][j] = scores[j][i] = pair_score(students[i], students[j])
    rng = random.Random(seed)
    odd = n % 2 == 1
    leftover = None
    idx = list(range(n))
    if odd:
        # the student with the lowest total compatibility joins a pair afterwards
        leftover = min(idx, key=lambda i: sum(scores[i]))
        idx.remove(leftover)
    sub = [[scores[i][j] for j in idx] for i in idx]
    pairs_local = _improve(_greedy(len(idx), sub, rng), sub)
    pairs = [(idx[i], idx[j]) for i, j in pairs_local]
    infos = [explain(students[i], students[j]) for i, j in pairs]
    if leftover is not None:
        best = max(range(len(pairs)), key=lambda k: scores[leftover][pairs[k][0]] + scores[leftover][pairs[k][1]])
        extra = students[leftover]
        info = infos[best]
        info.members.append(extra.name)
        a, b = pairs[best]
        for other in (students[a], students[b]):
            info.helps += [f"{extra.name} can help {other.name} with {s}" for s, _ in helps(extra, other)]
            info.helps += [f"{other.name} can help {extra.name} with {s}" for s, _ in helps(other, extra)]
        info.reasons.append(f"{extra.name} joins as a third member (odd cohort)")
        info.score = round(info.score + (scores[leftover][a] + scores[leftover][b]) / 2, 3)
    baseline = _random_baseline(n, scores, seed)
    total = round(sum(p.score for p in infos), 3)
    return Result(infos, total, round(baseline, 3), count_blocking(pairs, scores, n))


def _random_baseline(n: int, scores: list[list[float]], seed: int, trials: int = 50) -> float:
    rng = random.Random(seed + 1)
    totals = []
    for _ in range(trials):
        order = list(range(n))
        rng.shuffle(order)
        pairs = [(order[k], order[k + 1]) for k in range(0, n - 1, 2)]
        if n % 2 == 1:
            pairs.append((order[-1], order[0]))
        totals.append(_total(pairs, scores))
    return sum(totals) / len(totals)
