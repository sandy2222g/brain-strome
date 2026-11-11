"""Seat guests at tables: friends together, feuds apart.

A seating is a list of tables, each a list of guest names. Score = LIKE_POINTS for every liked pair sharing a
table, minus FEUD_PENALTY for every feuding pair sharing one. `plan` improves a starting seating by swapping two
guests whenever that raises the score (hill climbing), restarted from several seeded shuffles; the best result wins.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "guests.json"
LIKE_POINTS = 1
FEUD_PENALTY = 10
MAX_GUESTS = 60


class SeatingError(ValueError):
    """Invalid guest list."""


@dataclass(frozen=True)
class Party:
    guests: list[str]
    likes: frozenset[frozenset[str]]
    feuds: frozenset[frozenset[str]]
    tables: int
    seats: int


def build(guests: list[str], likes: list[list[str]], feuds: list[list[str]], tables: int, seats: int) -> Party:
    if tables < 1 or seats < 1:
        raise SeatingError("need at least one table and one seat")
    if not guests or len(guests) > MAX_GUESTS:
        raise SeatingError(f"between 1 and {MAX_GUESTS} guests")
    if len(set(guests)) != len(guests):
        raise SeatingError("guest names must be unique")
    if len(guests) > tables * seats:
        raise SeatingError("not enough seats")
    known = set(guests)
    for pair in [*likes, *feuds]:
        if len(pair) != 2 or pair[0] == pair[1] or not set(pair) <= known:
            raise SeatingError(f"bad pair {pair}")
    return Party(guests, frozenset(frozenset(p) for p in likes), frozenset(frozenset(p) for p in feuds), tables, seats)


def load(path: Path = DATA) -> Party:
    raw = json.loads(path.read_text())
    return build(raw["guests"], raw["likes"], raw["feuds"], raw["tables"], raw["seats"])


def score(party: Party, seating: list[list[str]]) -> int:
    total = 0
    for table in seating:
        for a, b in combinations(table, 2):
            pair = frozenset((a, b))
            total += LIKE_POINTS * (pair in party.likes) - FEUD_PENALTY * (pair in party.feuds)
    return total


def pairs_together(party: Party, seating: list[list[str]], kind: str) -> int:
    want = party.likes if kind == "likes" else party.feuds
    return sum(frozenset(p) in want for table in seating for p in combinations(table, 2))


def in_order(party: Party) -> list[list[str]]:
    """Baseline: fill table 1, then table 2, in list order."""
    return [party.guests[i : i + party.seats] for i in range(0, len(party.guests), party.seats)][: party.tables]


def _climb(party: Party, seating: list[list[str]]) -> list[list[str]]:
    """Swap two guests (or move one to a free seat) while that improves the score."""
    improved = True
    while improved:
        improved = False
        current = score(party, seating)
        spots = [(t, k) for t in range(len(seating)) for k in range(len(seating[t]))]
        for (t1, k1), (t2, k2) in combinations(spots, 2):
            if t1 == t2:
                continue
            seating[t1][k1], seating[t2][k2] = seating[t2][k2], seating[t1][k1]
            new = score(party, seating)
            if new > current:
                current, improved = new, True
            else:
                seating[t1][k1], seating[t2][k2] = seating[t2][k2], seating[t1][k1]
    return seating


def plan(party: Party, restarts: int = 25, seed: int = 0) -> list[list[str]]:
    rng = random.Random(seed)
    best = in_order(party)
    best_score = score(party, best)
    for _ in range(restarts):
        order = list(party.guests)
        rng.shuffle(order)
        seating = _climb(party, [order[i : i + party.seats] for i in range(0, len(order), party.seats)][: party.tables])
        s = score(party, seating)
        if s > best_score:
            best, best_score = seating, s
    return best
