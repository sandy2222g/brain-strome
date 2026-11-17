"""Split a photo timeline into albums wherever the gap exceeds a threshold."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "photos.json"


class AlbumError(ValueError):
    """Raised for invalid photo data."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _times(photos: list[dict[str, str]]) -> list[tuple[datetime, str]]:
    if not photos:
        raise AlbumError("need at least one photo")
    try:
        return sorted((datetime.fromisoformat(p["taken"]), p["file"]) for p in photos)
    except (ValueError, KeyError) as err:
        raise AlbumError(f"bad photo entry: {err}") from err


def _summary(items: list[tuple[datetime, str]]) -> dict[str, Any]:
    return {
        "start": items[0][0].isoformat(timespec="minutes"),
        "end": items[-1][0].isoformat(timespec="minutes"),
        "count": len(items),
        "files": [f for _, f in items],
    }


def group_by_gap(photos: list[dict[str, str]], gap_hours: float) -> list[dict[str, Any]]:
    """New album whenever the time since the previous photo is greater than `gap_hours`."""
    if gap_hours <= 0:
        raise AlbumError("gap_hours must be positive")
    items = _times(photos)
    limit = timedelta(hours=gap_hours)
    albums: list[list[tuple[datetime, str]]] = [[items[0]]]
    for prev, cur in zip(items, items[1:], strict=False):
        if cur[0] - prev[0] > limit:
            albums.append([])
        albums[-1].append(cur)
    return [_summary(a) for a in albums]


def group_by_day(photos: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Baseline: one album per calendar date, which cuts late-night events in two."""
    items = _times(photos)
    days: dict[str, list[tuple[datetime, str]]] = {}
    for it in items:
        days.setdefault(it[0].date().isoformat(), []).append(it)
    return [_summary(v) for v in days.values()]
