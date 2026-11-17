"""Knockout brackets with standard seeding, round-robin schedules, and a Monte Carlo fairness check."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "teams.json"


class BracketError(ValueError):
    pass


@dataclass(frozen=True)
class Team:
    name: str
    rating: float


def load_teams(path: Path = DATA) -> list[Team]:
    return [Team(n, float(r)) for n, r in json.loads(path.read_text())["teams"]]


def seed_order(size: int) -> list[int]:
    """Seeds in bracket order for a power-of-two field: 1 meets 2 only in the final, 1 plays the lowest seed first."""
    if size < 2 or size & (size - 1):
        raise BracketError("size must be a power of two, at least 2")
    order = [1]
    while len(order) < size:
        n = len(order) * 2
        order = [x for s in order for x in (s, n + 1 - s)]
    return order


def bracket_size(n: int) -> int:
    if n < 2:
        raise BracketError("need at least 2 teams")
    size = 2
    while size < n:
        size *= 2
    return size


def first_round(teams: list[Team]) -> list[tuple[Team | None, Team | None]]:
    """Pairs for round one, teams sorted best first; missing opponents are byes (None) for the top seeds."""
    ranked = sorted(teams, key=lambda t: -t.rating)
    size = bracket_size(len(ranked))
    slots: list[Team | None] = [ranked[s - 1] if s <= len(ranked) else None for s in seed_order(size)]
    return [(slots[i], slots[i + 1]) for i in range(0, size, 2)]


def win_prob(a: Team, b: Team) -> float:
    """Elo formula: a 400-point gap means roughly a 10-to-1 favourite."""
    return 1 / (1 + 10 ** ((b.rating - a.rating) / 400))


def play(a: Team | None, b: Team | None, rng: random.Random) -> Team:
    if a is None or b is None:
        return a or b  # type: ignore[return-value]
    return a if rng.random() < win_prob(a, b) else b


def run_knockout(pairs: list[tuple[Team | None, Team | None]], rng: random.Random) -> Team:
    cur = [play(a, b, rng) for a, b in pairs]
    while len(cur) > 1:
        cur = [play(cur[i], cur[i + 1], rng) for i in range(0, len(cur), 2)]
    return cur[0]


def round_robin(teams: list[Team]) -> list[list[tuple[Team, Team]]]:
    """Circle method: every team plays every other exactly once; an odd field gets a rest slot each round."""
    if len(teams) < 2:
        raise BracketError("need at least 2 teams")
    ring: list[Team | None] = list(teams) + ([None] if len(teams) % 2 else [])
    n = len(ring)
    rounds = []
    for _ in range(n - 1):
        rounds.append([(a, b) for a, b in zip(ring[: n // 2], ring[::-1][: n // 2], strict=True) if a and b])
        ring = [ring[0], ring[-1]] + ring[1:-1]
    return rounds


def run_round_robin(teams: list[Team], rng: random.Random) -> Team:
    pts = {t.name: 0.0 for t in teams}
    for rnd in round_robin(teams):
        for a, b in rnd:
            pts[play(a, b, rng).name] += 1
    best = max(pts.values())
    top = [t for t in teams if pts[t.name] == best]
    return rng.choice(top)  # break ties by a coin flip


def simulate(teams: list[Team], trials: int = 4000, seed: int = 1) -> dict[str, dict[str, float]]:
    """Chance each team wins under three formats: seeded knockout, random-draw knockout, round robin."""
    if not 100 <= trials <= 20000:
        raise BracketError("trials must be 100-20000")
    rng = random.Random(seed)
    seeded = first_round(teams)
    wins = {f: {t.name: 0 for t in teams} for f in ("seeded", "random", "round_robin")}
    size = bracket_size(len(teams))
    for _ in range(trials):
        wins["seeded"][run_knockout(seeded, rng).name] += 1
        shuffled = teams[:]
        rng.shuffle(shuffled)
        slots: list[Team | None] = shuffled + [None] * (size - len(shuffled))
        rng.shuffle(slots)
        wins["random"][run_knockout([(slots[i], slots[i + 1]) for i in range(0, size, 2)], rng).name] += 1
        wins["round_robin"][run_round_robin(teams, rng).name] += 1
    return {f: {n: round(w / trials, 4) for n, w in d.items()} for f, d in wins.items()}
