"""Timeboxing: choose and place tasks in the free gaps of a day.

Free gaps are the day window minus fixed events (each task also gets a small buffer after it).
A *set* of tasks is feasible if an earliest-deadline-first pass can place every task whole (tasks are
not split) before its deadline. We find the feasible set with the highest total priority exactly by
enumerating subsets (<= 14 tasks), and compare with the naive "do them in the order written" plan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "day.json"
MAX_TASKS = 14


class PlanError(ValueError):
    """Invalid input."""


@dataclass(frozen=True)
class Task:
    title: str
    minutes: int
    priority: int
    deadline: float | None = None  # hour of day


@dataclass(frozen=True)
class Event:
    title: str
    start: float
    end: float


@dataclass(frozen=True)
class Placed:
    title: str
    start: float
    end: float
    priority: int


def load(path: Path = DATA) -> dict[str, object]:
    raw = json.loads(path.read_text())
    return {
        "day_start": raw["day_start"],
        "day_end": raw["day_end"],
        "buffer_min": raw["buffer_min"],
        "events": [Event(**e) for e in raw["events"]],
        "tasks": [Task(**t) for t in raw["tasks"]],
    }


def free_gaps(day_start: float, day_end: float, events: list[Event]) -> list[tuple[float, float]]:
    if day_end <= day_start:
        raise PlanError("day must end after it starts")
    cur, gaps = day_start, []
    for e in sorted(events, key=lambda x: x.start):
        if e.end <= e.start:
            raise PlanError(f"event '{e.title}' ends before it starts")
        if e.start > cur:
            gaps.append((cur, min(e.start, day_end)))
        cur = max(cur, e.end)
    if cur < day_end:
        gaps.append((cur, day_end))
    return [(a, b) for a, b in gaps if b > a]


def place(tasks: list[Task], gaps: list[tuple[float, float]], buffer_min: int) -> list[Placed] | None:
    """Earliest-deadline-first, whole tasks, first gap that fits. None if some task cannot be placed in time."""
    pos = [a for a, _ in gaps]
    out: list[Placed] = []
    order = sorted(tasks, key=lambda t: (t.deadline if t.deadline is not None else 99.0, -t.priority, t.title))
    for t in order:
        need = (t.minutes + buffer_min) / 60
        for gi, (_, end) in enumerate(gaps):
            start = pos[gi]
            fin = start + t.minutes / 60
            if fin <= end + 1e-9:
                if t.deadline is not None and fin > t.deadline + 1e-9:
                    continue
                out.append(Placed(t.title, round(start, 4), round(fin, 4), t.priority))
                pos[gi] = start + need
                break
        else:
            return None
    return sorted(out, key=lambda p: p.start)


def validate(tasks: list[Task]) -> None:
    if len(tasks) > MAX_TASKS:
        raise PlanError(f"at most {MAX_TASKS} tasks")
    for t in tasks:
        if t.minutes <= 0 or not 1 <= t.priority <= 5:
            raise PlanError(f"bad task '{t.title}': minutes > 0 and priority 1-5 required")


def best_plan(tasks: list[Task], gaps: list[tuple[float, float]], buffer_min: int) -> list[Placed]:
    """Exact: the feasible subset with the largest total priority (ties: fewer minutes, then fewer tasks)."""
    validate(tasks)
    best: tuple[int, int, int] | None = None
    best_plan_: list[Placed] = []
    for r in range(len(tasks), -1, -1):
        for combo in combinations(tasks, r):
            score = (sum(t.priority for t in combo), -sum(t.minutes for t in combo), -len(combo))
            if best is not None and score <= best:
                continue
            placed = place(list(combo), gaps, buffer_min)
            if placed is not None:
                best, best_plan_ = score, placed
    return best_plan_


def in_order_plan(tasks: list[Task], gaps: list[tuple[float, float]], buffer_min: int) -> list[Placed]:
    """Baseline: take tasks in the order written, add each one only if the day still works."""
    chosen: list[Task] = []
    out: list[Placed] = []
    for t in tasks:
        placed = place([*chosen, t], gaps, buffer_min)
        if placed is not None:
            chosen.append(t)
            out = placed
    return out


def total_priority(plan: list[Placed]) -> int:
    return sum(p.priority for p in plan)


def hhmm(h: float) -> str:
    m = round(h * 60)
    return f"{m // 60:02d}:{m % 60:02d}"
