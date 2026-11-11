"""Fair chore rota: who does which chore each week.

Round-robin ignores that people hate different chores and that chores differ in effort. `fair_rota` picks, week by
week, the assignment (every chore to a different person) with the lowest cost. Cost is how much the person dislikes
the chore, plus a quadratic penalty on each person's running workload (a linear one cancels out when everyone
works), plus a nudge against repeating last week's chore. The best assignment each week is found exactly by trying
all of them, so people and chores stay small.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import permutations
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "household.json"
MAX_PEOPLE = 7


class RotaError(ValueError):
    """Invalid household."""


@dataclass(frozen=True)
class Chore:
    name: str
    effort: int  # points of work per week


@dataclass(frozen=True)
class Person:
    name: str
    dislike: dict[str, int]  # chore name -> 1 (fine) .. 5 (hate it)


def load(path: Path = DATA) -> tuple[list[Person], list[Chore]]:
    raw = json.loads(path.read_text())
    return [Person(p["name"], p["dislike"]) for p in raw["people"]], [
        Chore(c["name"], c["effort"]) for c in raw["chores"]
    ]


def validate(people: list[Person], chores: list[Chore], weeks: int) -> None:
    if not 1 <= weeks <= 52:
        raise RotaError("weeks must be between 1 and 52")
    if not chores or not people:
        raise RotaError("need at least one person and one chore")
    if len(people) > MAX_PEOPLE:
        raise RotaError(f"at most {MAX_PEOPLE} people")
    if len(chores) > len(people):
        raise RotaError("more chores than people: someone would do two chores a week")
    if len({p.name for p in people}) != len(people) or len({c.name for c in chores}) != len(chores):
        raise RotaError("names must be unique")
    for p in people:
        for c in chores:
            if not 1 <= p.dislike.get(c.name, 0) <= 5:
                raise RotaError(f"{p.name}: dislike of '{c.name}' must be 1 to 5")
        if any(c.effort <= 0 for c in chores):
            raise RotaError("effort must be positive")


Rota = list[list[int]]  # rota[week][chore index] = person index


def round_robin(people: list[Person], chores: list[Chore], weeks: int) -> Rota:
    """Baseline: shift every chore one person along each week."""
    validate(people, chores, weeks)
    return [[(c + w) % len(people) for c in range(len(chores))] for w in range(weeks)]


def fair_rota(
    people: list[Person], chores: list[Chore], weeks: int, balance: float = 6.0, repeat_penalty: float = 1.5
) -> Rota:
    validate(people, chores, weeks)
    load = [0.0] * len(people)
    mean_effort = sum(c.effort for c in chores) / len(chores)
    rota: Rota = []
    prev: dict[int, int] = {}  # person -> chore they did last week
    for _ in range(weeks):
        best: tuple[float, tuple[int, ...]] | None = None
        for perm in permutations(range(len(people)), len(chores)):
            cost = 0.0
            for ci, pi in enumerate(perm):
                cost += people[pi].dislike[chores[ci].name]
                cost += balance * ((load[pi] + chores[ci].effort) / mean_effort) ** 2 / len(chores)
                if prev.get(pi) == ci:
                    cost += repeat_penalty
            if best is None or cost < best[0] - 1e-9:
                best = (cost, perm)
        assert best is not None
        perm = best[1]
        for ci, pi in enumerate(perm):
            load[pi] += chores[ci].effort
        prev = {pi: ci for ci, pi in enumerate(perm)}
        rota.append(list(perm))
    return rota


def efforts(rota: Rota, chores: list[Chore], n_people: int) -> list[int]:
    out = [0] * n_people
    for week in rota:
        for ci, pi in enumerate(week):
            out[pi] += chores[ci].effort
    return out


def total_dislike(rota: Rota, people: list[Person], chores: list[Chore]) -> int:
    return sum(people[pi].dislike[chores[ci].name] for week in rota for ci, pi in enumerate(week))


def effort_spread(rota: Rota, chores: list[Chore], n_people: int) -> int:
    e = efforts(rota, chores, n_people)
    return max(e) - min(e)


def worst_streak(rota: Rota) -> int:
    """Longest run of weeks in which the same person does the same chore."""
    best = 1
    for ci in range(len(rota[0])):
        run = 1
        for w in range(1, len(rota)):
            run = run + 1 if rota[w][ci] == rota[w - 1][ci] else 1
            best = max(best, run)
    return best
