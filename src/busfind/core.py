"""Departures generated from first/last times and a headway; handles after-midnight routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "timetable.json"
DAY = 1440


class BusError(ValueError):
    """Raised for invalid times or routes."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def parse(t: str) -> int:
    try:
        h, m = t.split(":")
        hh, mm = int(h), int(m)
    except ValueError as err:
        raise BusError(f"bad time {t!r}, use HH:MM") from err
    if not (0 <= hh < 24 and 0 <= mm < 60):
        raise BusError(f"bad time {t!r}")
    return hh * 60 + mm


def fmt(minutes: int) -> str:
    m = minutes % DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def departures(first: str, last: str, headway: int) -> list[int]:
    """Departure minutes from `first`; a `last` earlier than `first` means it runs past midnight."""
    if headway < 1:
        raise BusError("headway must be at least 1 minute")
    start, end = parse(first), parse(last)
    if end < start:
        end += DAY
    return list(range(start, end + 1, headway))


def next_departures(route: dict[str, Any], now: str, walk_min: int = 0, count: int = 3) -> dict[str, Any]:
    """Next catchable departures after `now + walk_min`, looking into the next day if needed."""
    if walk_min < 0 or count < 1:
        raise BusError("bad walk or count")
    deps = departures(route["first"], route["last"], int(route["headway_min"]))
    ready = parse(now) + walk_min
    # consider today's and tomorrow's runs, so a route that has finished shows tomorrow's first bus
    pool = sorted({d + k * DAY for d in deps for k in (-1, 0, 1)})
    upcoming = [d for d in pool if d >= ready][:count]
    return {
        "route": route["name"],
        "next": [{"time": fmt(d), "in_min": d - parse(now), "tomorrow": d >= DAY} for d in upcoming],
        "is_last": bool(upcoming) and upcoming[0] == deps[-1] and upcoming[0] >= ready,
    }


def board(routes: list[dict[str, Any]], now: str, walk_min: int = 0) -> list[dict[str, Any]]:
    if not routes:
        raise BusError("need at least one route")
    rows = [next_departures(r, now, walk_min) for r in routes]
    rows.sort(key=lambda r: (r["next"][0]["in_min"], r["route"]))
    return rows
