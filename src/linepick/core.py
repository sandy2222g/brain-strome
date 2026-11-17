"""Expected wait for each checkout line, and the best eligible one."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "lanes.json"


class LineError(ValueError):
    """Raised for invalid lane or basket input."""


@dataclass(frozen=True)
class Lane:
    name: str
    seconds_per_item: float
    overhead: float
    ahead: tuple[int, ...]
    item_limit: int | None = None


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def build(raw: list[dict[str, Any]]) -> list[Lane]:
    if not raw:
        raise LineError("need at least one lane")
    lanes = []
    for r in raw:
        speed, over = float(r["seconds_per_item"]), float(r["overhead"])
        ahead = tuple(int(n) for n in r["ahead"])
        limit = r.get("item_limit")
        if speed <= 0 or over < 0 or any(n < 0 for n in ahead):
            raise LineError(f"bad numbers for lane {r['name']!r}")
        if limit is not None and int(limit) < 1:
            raise LineError(f"bad item limit for lane {r['name']!r}")
        lanes.append(Lane(str(r["name"]), speed, over, ahead, None if limit is None else int(limit)))
    if len({lane.name for lane in lanes}) != len(lanes):
        raise LineError("lane names must be unique")
    return lanes


def _serve(lane: Lane, items: int) -> float:
    return lane.overhead + items * lane.seconds_per_item


def wait_seconds(lane: Lane, items: int) -> float:
    """Time until my basket is finished: everyone ahead, then me."""
    if items < 1:
        raise LineError("basket must have at least one item")
    return round(sum(_serve(lane, n) for n in lane.ahead) + _serve(lane, items), 2)


def eligible(lane: Lane, items: int) -> bool:
    return lane.item_limit is None or items <= lane.item_limit


def rank(lanes: list[Lane], items: int) -> list[dict[str, Any]]:
    """Eligible lanes fastest first (ties by name), then ineligible ones."""
    rows = [
        {
            "name": lane.name,
            "people_ahead": len(lane.ahead),
            "eligible": eligible(lane, items),
            "seconds": wait_seconds(lane, items) if eligible(lane, items) else None,
        }
        for lane in lanes
    ]
    rows.sort(key=lambda r: (not r["eligible"], r["seconds"] if r["seconds"] is not None else 0, r["name"]))
    return rows


def fewest_people(lanes: list[Lane], items: int) -> str:
    """Baseline: the eligible lane with the shortest queue (ties by name)."""
    ok = [lane for lane in lanes if eligible(lane, items)]
    if not ok:
        raise LineError("no lane accepts this basket")
    return min(ok, key=lambda lane: (len(lane.ahead), lane.name)).name
