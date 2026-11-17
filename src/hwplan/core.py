"""Moore-Hodgson: the largest set of tasks that can all finish by their deadlines."""

from __future__ import annotations

import heapq
import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "homework.json"


class PlanError(ValueError):
    """Raised for invalid tasks."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _tasks(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw:
        raise PlanError("need at least one task")
    out = []
    for t in raw:
        hours, due = float(t["hours"]), float(t["due"])
        if hours <= 0 or due <= 0:
            raise PlanError(f"hours and due must be positive for {t['name']!r}")
        out.append({"name": str(t["name"]), "hours": hours, "due": due})
    return out


def moore_hodgson(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Maximise the number of tasks finished on time (one worker, no breaks).

    Take tasks by due date; whenever the running total passes a due date, drop the longest task taken so far.
    Dropped tasks are done last.
    """
    tasks = sorted(_tasks(raw), key=lambda t: (t["due"], t["name"]))
    heap: list[tuple[float, str, dict[str, Any]]] = []
    total = 0.0
    late: list[dict[str, Any]] = []
    for t in tasks:
        heapq.heappush(heap, (-t["hours"], t["name"], t))
        total += t["hours"]
        if total > t["due"]:
            _, _, longest = heapq.heappop(heap)
            total -= longest["hours"]
            late.append(longest)
    on_time = sorted((h[2] for h in heap), key=lambda t: (t["due"], t["name"]))
    return _timeline(on_time, sorted(late, key=lambda t: (t["due"], t["name"])))


def _timeline(on_time: list[dict[str, Any]], late: list[dict[str, Any]]) -> dict[str, Any]:
    clock, rows = 0.0, []
    for t in on_time + late:
        clock += t["hours"]
        rows.append({**t, "finish": clock, "on_time": clock <= t["due"]})
    return {"schedule": rows, "on_time_count": sum(r["on_time"] for r in rows), "total_hours": clock}


def in_order(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Baseline: do the tasks in the order listed."""
    return _timeline(_tasks(raw), [])


def shortest_first(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Baseline: shortest task first."""
    return _timeline(sorted(_tasks(raw), key=lambda t: (t["hours"], t["name"])), [])
