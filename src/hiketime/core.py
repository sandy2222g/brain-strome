"""Naismith's rule: walking time from distance, plus extra time for every metre climbed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "trail.json"
DAY = 1440


class HikeError(ValueError):
    """Raised for invalid trail data."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def parse(t: str) -> int:
    try:
        h, m = t.split(":")
        hh, mm = int(h), int(m)
    except ValueError as err:
        raise HikeError(f"bad time {t!r}, use HH:MM") from err
    if not (0 <= hh < 24 and 0 <= mm < 60):
        raise HikeError(f"bad time {t!r}")
    return hh * 60 + mm


def fmt(minutes: float) -> str:
    m = round(minutes) % DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def legs(points: list[dict[str, Any]], pace_kmh: float, ascent_min_per_100m: float) -> list[dict[str, Any]]:
    """Walking minutes per leg: distance / pace plus extra time per 100 m climbed (descent gets no credit)."""
    if len(points) < 2:
        raise HikeError("need at least two points")
    if pace_kmh <= 0 or ascent_min_per_100m < 0:
        raise HikeError("bad pace or ascent time")
    out = []
    for a, b in zip(points, points[1:], strict=False):
        km = float(b["km"]) - float(a["km"])
        if km <= 0:
            raise HikeError(f"distance must increase at {b['name']!r}")
        climb = max(0.0, float(b["height"]) - float(a["height"]))
        walk = km / pace_kmh * 60
        extra = climb / 100 * ascent_min_per_100m
        out.append({"from": a["name"], "to": b["name"], "km": round(km, 2), "climb": climb,
                    "minutes": round(walk + extra, 1)})
    return out


def estimate(trail: dict[str, Any]) -> dict[str, Any]:
    ls = legs(trail["points"], float(trail["pace_kmh"]), float(trail["ascent_min_per_100m"]))
    moving = sum(x["minutes"] for x in ls)
    rest = moving / 60 * float(trail["rest_min_per_hour"])
    total = moving + rest
    km = sum(x["km"] for x in ls)
    naive = km / float(trail["pace_kmh"]) * 60  # distance-only guess
    latest = parse(trail["sunset"]) - total - 30  # keep a 30 minute margin before sunset
    return {
        "legs": ls,
        "moving_min": round(moving, 1),
        "rest_min": round(rest, 1),
        "total_min": round(total, 1),
        "total_km": round(km, 2),
        "total_climb": sum(x["climb"] for x in ls),
        "distance_only_min": round(naive, 1),
        "underestimate_min": round(total - naive, 1),
        "latest_start": fmt(latest),
    }
