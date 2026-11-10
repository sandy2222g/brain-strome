"""Seating as an optimisation problem, solved with simulated annealing.

Hard rules: table capacity, "together" groups share a table, "apart" pairs never do.
Soft goals: maximise the affinity of people who share a table (likes, same social group,
dislikes cost a lot). Everything is deterministic for a given seed.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations

LIKE = 8.0
SAME_GROUP = 1.0
DISLIKE = -12.0
APART_PENALTY = -1000.0


class SeatingError(ValueError):
    """The request cannot be satisfied or is malformed; the message is safe to show."""


@dataclass(frozen=True)
class Guest:
    name: str
    group: str = ""


@dataclass
class Problem:
    guests: list[Guest]
    likes: list[tuple[str, str]] = field(default_factory=list)
    dislikes: list[tuple[str, str]] = field(default_factory=list)
    together: list[list[str]] = field(default_factory=list)
    apart: list[tuple[str, str]] = field(default_factory=list)
    table_size: int = 8


@dataclass
class Solution:
    tables: list[list[str]]
    score: float
    random_baseline: float
    violations: list[str]
    table_scores: list[float]
    happiness: dict[str, float]
    reasons: dict[str, list[str]]


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


class Scorer:
    def __init__(self, problem: Problem) -> None:
        names = [g.name for g in problem.guests]
        if len(set(names)) != len(names):
            raise SeatingError("guest names must be unique")
        known = set(names)
        for pair in [*problem.likes, *problem.dislikes, *problem.apart]:
            for n in pair:
                if n not in known:
                    raise SeatingError(f"unknown guest in a rule: {n}")
        for grp in problem.together:
            for n in grp:
                if n not in known:
                    raise SeatingError(f"unknown guest in a rule: {n}")
        self.affinity: dict[tuple[str, str], float] = defaultdict(float)
        self.reason: dict[tuple[str, str], list[str]] = defaultdict(list)
        for a, b in combinations(problem.guests, 2):
            if a.group and a.group == b.group:
                self.affinity[_pair_key(a.name, b.name)] += SAME_GROUP
                self.reason[_pair_key(a.name, b.name)].append(f"both in {a.group}")
        for a, b in problem.likes:
            self.affinity[_pair_key(a, b)] += LIKE
            self.reason[_pair_key(a, b)].append("wanted to sit together")
        for a, b in problem.dislikes:
            self.affinity[_pair_key(a, b)] += DISLIKE
            self.reason[_pair_key(a, b)].append("would rather not sit together")
        self.apart = {_pair_key(a, b) for a, b in problem.apart}

    def table_score(self, members: list[str], hard: bool = True) -> float:
        total = 0.0
        for a, b in combinations(members, 2):
            k = _pair_key(a, b)
            total += self.affinity.get(k, 0.0)
            if hard and k in self.apart:
                total += APART_PENALTY
        return total


def _units(problem: Problem) -> list[list[str]]:
    """Merge 'together' groups into units that always move as one."""
    parent = {g.name: g.name for g in problem.guests}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for grp in problem.together:
        for other in grp[1:]:
            parent[find(other)] = find(grp[0])
    units: dict[str, list[str]] = defaultdict(list)
    for g in problem.guests:
        units[find(g.name)].append(g.name)
    return list(units.values())


def solve(problem: Problem, seed: int = 0, iterations: int = 20000) -> Solution:
    n = len(problem.guests)
    if n == 0:
        raise SeatingError("add at least one guest")
    if problem.table_size < 1:
        raise SeatingError("table size must be at least 1")
    scorer = Scorer(problem)
    units = _units(problem)
    biggest = max(len(u) for u in units)
    if biggest > problem.table_size:
        raise SeatingError(f"a group that must sit together has {biggest} people but tables seat {problem.table_size}")
    n_tables = math.ceil(n / problem.table_size)
    # Allow one spare table when whole groups cannot be packed tightly.
    for extra in (0, 1):
        rng = random.Random(seed)
        assign = _initial(units, n_tables + extra, problem.table_size, rng)
        if assign is not None:
            n_tables += extra
            break
    else:
        raise SeatingError("could not fit the groups onto the tables")
    tables: list[list[int]] = [[] for _ in range(n_tables)]
    for ui, t in enumerate(assign):
        tables[t].append(ui)

    def members(t: int) -> list[str]:
        return [name for ui in tables[t] for name in units[ui]]

    def size(t: int) -> int:
        return sum(len(units[ui]) for ui in tables[t])

    scores = [scorer.table_score(members(t)) for t in range(n_tables)]
    cur = sum(scores)
    best, best_tables = cur, [list(t) for t in tables]
    temp0 = 4.0
    for it in range(iterations):
        temp = temp0 * (1 - it / iterations) + 0.01
        t1 = rng.randrange(n_tables)
        if not tables[t1]:
            continue
        u1 = rng.choice(tables[t1])
        t2 = rng.randrange(n_tables)
        if t2 == t1:
            continue
        if tables[t2] and rng.random() < 0.7:
            u2 = rng.choice(tables[t2])
            if size(t1) - len(units[u1]) + len(units[u2]) > problem.table_size:
                continue
            if size(t2) - len(units[u2]) + len(units[u1]) > problem.table_size:
                continue
            tables[t1].remove(u1)
            tables[t2].remove(u2)
            tables[t1].append(u2)
            tables[t2].append(u1)
            undo = ("swap", u1, u2)
        else:
            if size(t2) + len(units[u1]) > problem.table_size:
                continue
            tables[t1].remove(u1)
            tables[t2].append(u1)
            undo = ("move", u1, None)
        s1, s2 = scorer.table_score(members(t1)), scorer.table_score(members(t2))
        delta = (s1 + s2) - (scores[t1] + scores[t2])
        if delta >= 0 or rng.random() < math.exp(delta / temp):
            scores[t1], scores[t2] = s1, s2
            cur += delta
            if cur > best:
                best, best_tables = cur, [list(t) for t in tables]
        else:
            if undo[0] == "swap":
                tables[t1].remove(undo[2])  # type: ignore[arg-type]
                tables[t2].remove(undo[1])
                tables[t1].append(undo[1])
                tables[t2].append(undo[2])  # type: ignore[arg-type]
            else:
                tables[t2].remove(undo[1])
                tables[t1].append(undo[1])
    final = [[name for ui in t for name in units[ui]] for t in best_tables if t]
    return describe(problem, final, scorer, seed)


def _initial(units: list[list[str]], n_tables: int, cap: int, rng: random.Random) -> list[int] | None:
    order = sorted(range(len(units)), key=lambda i: (-len(units[i]), rng.random()))
    load = [0] * n_tables
    assign = [0] * len(units)
    for ui in order:
        fits = [t for t in range(n_tables) if load[t] + len(units[ui]) <= cap]
        if not fits:
            return None
        t = min(fits, key=lambda x: (load[x], rng.random()))
        assign[ui] = t
        load[t] += len(units[ui])
    return assign


def describe(problem: Problem, tables: list[list[str]], scorer: Scorer, seed: int = 0) -> Solution:
    """Score a given arrangement (also used for manual edits) and explain it."""
    seated = [n for t in tables for n in t]
    names = {g.name for g in problem.guests}
    if sorted(seated) != sorted(names):
        raise SeatingError("every guest must be seated exactly once")
    if any(len(t) > problem.table_size for t in tables):
        raise SeatingError(f"a table has more than {problem.table_size} guests")
    table_scores = [scorer.table_score(t) for t in tables]
    violations: list[str] = []
    where = {n: i for i, t in enumerate(tables) for n in t}
    for a, b in sorted(scorer.apart):
        if where[a] == where[b]:
            violations.append(f"{a} and {b} must be apart but share table {where[a] + 1}")
    for grp in problem.together:
        if len({where[n] for n in grp}) > 1:
            violations.append("together group is split: " + ", ".join(grp))
    happiness: dict[str, float] = {}
    reasons: dict[str, list[str]] = {}
    for t in tables:
        for n in t:
            others = [o for o in t if o != n]
            happiness[n] = round(sum(scorer.affinity.get(_pair_key(n, o), 0.0) for o in others), 1)
            best = sorted(others, key=lambda o: -scorer.affinity.get(_pair_key(n, o), 0.0))[:2]
            reasons[n] = [
                f"{o}: {', '.join(scorer.reason[_pair_key(n, o)])}" for o in best if scorer.reason.get(_pair_key(n, o))
            ]
    return Solution(
        tables=[list(t) for t in tables],
        score=round(sum(table_scores), 1),
        random_baseline=round(random_baseline(problem, scorer, seed), 1),
        violations=violations,
        table_scores=[round(s, 1) for s in table_scores],
        happiness=happiness,
        reasons=reasons,
    )


def random_baseline(problem: Problem, scorer: Scorer, seed: int, trials: int = 30) -> float:
    """Average soft score of random capacity-respecting seatings: what you get without optimising."""
    rng = random.Random(seed + 1)
    units = _units(problem)
    n_tables = math.ceil(len(problem.guests) / problem.table_size) + 1
    scores = []
    for _ in range(trials):
        assign = _initial(units, n_tables, problem.table_size, rng)
        if assign is None:
            continue
        tables: list[list[str]] = [[] for _ in range(n_tables)]
        for ui, t in enumerate(assign):
            tables[t].extend(units[ui])
        scores.append(sum(scorer.table_score(t, hard=False) for t in tables))
    return sum(scores) / len(scores) if scores else 0.0
