"""Weekly strength planner: spread exercises over training days with muscle recovery gaps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "exercises.json"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class PlanError(ValueError):
    """Invalid planning request."""


@dataclass(frozen=True)
class Exercise:
    name: str
    muscles: tuple[str, ...]
    minutes: int


def load(path: Path = DATA) -> dict[str, Exercise]:
    return {
        e["name"]: Exercise(e["name"], tuple(e["muscles"]), e["minutes"])
        for e in json.loads(path.read_text())["exercises"]
    }


def pick_days(n: int) -> list[int]:
    """Spread n training days as evenly as possible over the week (indices 0-6)."""
    if not 1 <= n <= 7:
        raise PlanError("days per week must be 1-7")
    return [i * 7 // n for i in range(n)] if n < 7 else list(range(7))


def plan(names: list[str], train_days: int, minutes_per_day: int, gap_slots: int = 1) -> dict[str, object]:
    """Greedy: place each exercise (hardest muscles first) on the day with room and the least clash.

    Training days are spaced evenly; `gap_slots` is the minimum number of training slots between two
    sessions of the same muscle (1 = not in consecutive sessions).
    """
    ex = load()
    unknown = [n for n in names if n not in ex]
    if unknown:
        raise PlanError(f"unknown exercises: {', '.join(unknown)}")
    if not names:
        raise PlanError("pick at least one exercise")
    slots = pick_days(train_days)
    sessions: list[list[Exercise]] = [[] for _ in slots]
    unplaced: list[str] = []
    for e in sorted((ex[n] for n in names), key=lambda x: (-len(x.muscles), -x.minutes, x.name)):
        best, best_key = None, None
        for i, s in enumerate(sessions):
            if sum(x.minutes for x in s) + e.minutes > minutes_per_day:
                continue
            near = [j for j in range(len(sessions)) if abs(j - i) <= gap_slots and j != i]
            clash = sum(1 for j in near for x in sessions[j] if set(x.muscles) & set(e.muscles))
            same = sum(1 for x in s if set(x.muscles) & set(e.muscles))
            key = (clash, -same, sum(x.minutes for x in s))
            if best_key is None or key < best_key:
                best, best_key = i, key
        if best is None:
            unplaced.append(e.name)
        else:
            sessions[best].append(e)
    week = {DAYS[d]: [x.name for x in s] for d, s in zip(slots, sessions, strict=True)}
    clashes = sum(
        1
        for i in range(len(sessions))
        for j in range(i + 1, min(i + 1 + gap_slots, len(sessions)))
        for a in sessions[i]
        for b in sessions[j]
        if set(a.muscles) & set(b.muscles)
    )
    return {
        "week": week,
        "minutes": {DAYS[d]: sum(x.minutes for x in s) for d, s in zip(slots, sessions, strict=True)},
        "unplaced": unplaced,
        "recovery_clashes": clashes,
    }
