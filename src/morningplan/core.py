"""Critical-path scheduling: tasks can overlap unless one has to wait for another."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "routine.json"
DAY = 1440


class RoutineError(ValueError):
    """Raised for invalid tasks, cycles or times."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def parse(t: str) -> int:
    try:
        h, m = t.split(":")
        hh, mm = int(h), int(m)
    except ValueError as err:
        raise RoutineError(f"bad time {t!r}, use HH:MM") from err
    if not (0 <= hh < 24 and 0 <= mm < 60):
        raise RoutineError(f"bad time {t!r}")
    return hh * 60 + mm


def fmt(minutes: int) -> str:
    m = minutes % DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def _validate(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not tasks:
        raise RoutineError("need at least one task")
    by_name = {t["name"]: t for t in tasks}
    if len(by_name) != len(tasks):
        raise RoutineError("task names must be unique")
    for t in tasks:
        if int(t["min"]) <= 0:
            raise RoutineError(f"minutes must be positive for {t['name']!r}")
        for dep in t["after"]:
            if dep not in by_name:
                raise RoutineError(f"{t['name']!r} waits for unknown task {dep!r}")
    return by_name


def tails(by_name: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Longest chain of work from the start of each task to the end of the routine; detects loops."""
    succ: dict[str, list[str]] = {n: [] for n in by_name}
    for n, t in by_name.items():
        for dep in t["after"]:
            succ[dep].append(n)
    memo: dict[str, int] = {}
    visiting: set[str] = set()

    def go(n: str) -> int:
        if n in memo:
            return memo[n]
        if n in visiting:
            raise RoutineError("tasks wait for each other in a loop")
        visiting.add(n)
        memo[n] = int(by_name[n]["min"]) + max((go(m) for m in succ[n]), default=0)
        visiting.discard(n)
        return memo[n]

    return {n: go(n) for n in by_name}


def schedule(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """One person: hands-free tasks (kettle, toaster) run alone, other tasks are done one at a time.

    Whenever the person is free they take the ready task with the longest chain of work still behind it.
    """
    by_name = _validate(tasks)
    tail = tails(by_name)
    end: dict[str, int] = {}
    start: dict[str, int] = {}
    free_at = 0
    remaining = set(by_name)
    while remaining:
        progressed = False
        # hands-free tasks begin the moment their prerequisites are finished
        for n in sorted(remaining):
            t = by_name[n]
            if t.get("hands_free") and all(d in end for d in t["after"]):
                start[n] = max((end[d] for d in t["after"]), default=0)
                end[n] = start[n] + int(t["min"])
                remaining.discard(n)
                progressed = True
        ready = [
            n for n in remaining
            if not by_name[n].get("hands_free") and all(d in end for d in by_name[n]["after"])
        ]
        if ready:
            def ready_at(n: str) -> int:
                return max((end[d] for d in by_name[n]["after"]), default=0)

            now = max(free_at, min(ready_at(n) for n in ready))
            can = [n for n in ready if ready_at(n) <= now]
            pick = max(can, key=lambda n: (tail[n], n))
            start[pick] = now
            end[pick] = now + int(by_name[pick]["min"])
            free_at = end[pick]
            remaining.discard(pick)
            progressed = True
        if not progressed:
            raise RoutineError("tasks wait for each other in a loop")
    total = max(end.values())
    rows = [
        {"name": n, "start": start[n], "end": end[n], "hands_free": bool(by_name[n].get("hands_free"))}
        for n in by_name
    ]
    rows.sort(key=lambda r: (r["start"], r["name"]))
    return {"rows": rows, "total": total, "lower_bound": max(tail.values())}


def wake_time(leave: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    plan = schedule(tasks)
    one_by_one = sum(int(t["min"]) for t in tasks)
    return {
        **plan,
        "wake": fmt(parse(leave) - plan["total"]),
        "one_at_a_time": one_by_one,
        "wake_one_at_a_time": fmt(parse(leave) - one_by_one),
    }
