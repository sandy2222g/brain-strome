"""Backward scheduling of a multi-dish meal so every dish is ready at the serving time.

Each dish is a chain of steps. Each step uses one resource (oven, hob, hands) of limited capacity.
We schedule from the serving time backwards: the last step of every dish ends at the serving time (or
as late as its resource allows), and earlier steps end where the next step starts, each pushed earlier
until its resource has a free slot. Time is in whole minutes before serving (0 = serve, larger = earlier).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "menu.json"


class MealError(ValueError):
    """Invalid menu."""


@dataclass(frozen=True)
class Step:
    dish: str
    step: str
    minutes: int
    resource: str


@dataclass(frozen=True)
class Slot:
    dish: str
    step: str
    resource: str
    start: int  # minutes before serving when the step starts
    end: int  # minutes before serving when it ends (end < start)


def load(path: Path = DATA) -> tuple[dict[str, int], list[list[Step]]]:
    raw = json.loads(path.read_text())
    dishes = [[Step(d["name"], s["step"], s["minutes"], s["resource"]) for s in d["steps"]] for d in raw["dishes"]]
    return raw["capacity"], dishes


def validate(capacity: dict[str, int], dishes: list[list[Step]]) -> None:
    if not dishes or any(not d for d in dishes):
        raise MealError("every dish needs at least one step")
    for d in dishes:
        for s in d:
            if s.minutes <= 0:
                raise MealError(f"{s.dish}: '{s.step}' needs a positive duration")
            if capacity.get(s.resource, 0) < 1:
                raise MealError(f"{s.dish}: no capacity for resource '{s.resource}'")


def _free(usage: dict[str, list[int]], cap: int, res: str, start: int, end: int) -> bool:
    """Is `res` under capacity for every minute in [end, start) (minutes before serving)?"""
    return all(usage[res][m] < cap for m in range(end, start))


def sync_schedule(capacity: dict[str, int], dishes: list[list[Step]], horizon: int = 600) -> list[Slot]:
    """Latest-start schedule: all dishes finish together at serving time when resources allow."""
    validate(capacity, dishes)
    usage = {r: [0] * horizon for r in capacity}
    slots: list[Slot] = []
    order = sorted(range(len(dishes)), key=lambda i: -sum(s.minutes for s in dishes[i]))
    # Place every dish's last step first, then work backwards a step at a time, longest dishes first.
    ends = {i: 0 for i in order}
    pending = {i: list(reversed(dishes[i])) for i in order}
    while any(pending.values()):
        for i in order:
            if not pending[i]:
                continue
            s = pending[i].pop(0)
            end = ends[i]
            while True:
                start = end + s.minutes
                if start > horizon:
                    raise MealError("the meal does not fit in the planning horizon")
                if _free(usage, capacity[s.resource], s.resource, start, end):
                    break
                end += 1
            for m in range(end, start):
                usage[s.resource][m] += 1
            slots.append(Slot(s.dish, s.step, s.resource, start, end))
            ends[i] = start
    return sorted(slots, key=lambda x: -x.start)


def sequential_schedule(capacity: dict[str, int], dishes: list[list[Step]], horizon: int = 900) -> list[Slot]:
    """Baseline: start every dish at time zero, in the order written, as soon as its resource is free.

    Returns slots in 'minutes since cooking began' converted so that the *last* dish to finish defines serving.
    """
    validate(capacity, dishes)
    free_at: dict[str, list[int]] = {r: [0] * c for r, c in capacity.items()}
    raw: list[tuple[Step, int, int]] = []
    for d in dishes:
        t = 0
        for s in d:
            slot = min(range(len(free_at[s.resource])), key=lambda k: max(free_at[s.resource][k], t))
            begin = max(free_at[s.resource][slot], t)
            fin = begin + s.minutes
            free_at[s.resource][slot] = fin
            raw.append((s, begin, fin))
            t = fin
    total = max(f for _, _, f in raw)
    if total > horizon:
        raise MealError("the meal does not fit in the planning horizon")
    return sorted(
        (Slot(s.dish, s.step, s.resource, total - b, total - f) for s, b, f in raw),
        key=lambda x: -x.start,
    )


def finish_times(slots: list[Slot]) -> dict[str, int]:
    """Minutes before serving at which each dish's last step ends (0 = ready exactly at serving)."""
    out: dict[str, int] = {}
    for s in slots:
        out[s.dish] = min(out.get(s.dish, 10**9), s.end)
    return out


def waiting_minutes(slots: list[Slot]) -> int:
    """Total minutes cooked food sits waiting: gaps between a dish's steps plus time after its last step."""
    by_dish: dict[str, list[Slot]] = {}
    for s in slots:
        by_dish.setdefault(s.dish, []).append(s)
    total = 0
    for items in by_dish.values():
        items.sort(key=lambda x: -x.start)
        total += sum(max(0, prev.end - nxt.start) for prev, nxt in zip(items, items[1:], strict=False))
        total += items[-1].end
    return total


def span(slots: list[Slot]) -> int:
    return max(s.start for s in slots)


def peak_usage(slots: list[Slot], resource: str) -> int:
    marks: dict[int, int] = {}
    for s in slots:
        if s.resource == resource:
            for m in range(s.end, s.start):
                marks[m] = marks.get(m, 0) + 1
    return max(marks.values(), default=0)
