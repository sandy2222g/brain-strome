"""Bedtime options counted back from a wake-up time in whole sleep cycles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "sample.json"
DAY = 1440


class SleepError(ValueError):
    """Raised for invalid times or settings."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def parse(t: str) -> int:
    try:
        h, m = t.split(":")
        hh, mm = int(h), int(m)
    except ValueError as err:
        raise SleepError(f"bad time {t!r}, use HH:MM") from err
    if not (0 <= hh < 24 and 0 <= mm < 60):
        raise SleepError(f"bad time {t!r}")
    return hh * 60 + mm


def fmt(minutes: int) -> str:
    m = minutes % DAY
    return f"{m // 60:02d}:{m % 60:02d}"


def bedtimes(
    wake: str, latency: int = 15, cycle: int = 90, cycles: tuple[int, ...] = (6, 5, 4, 3)
) -> list[dict[str, Any]]:
    """In-bed times so that `n` full cycles end exactly at `wake`, after `latency` minutes to fall asleep."""
    if latency < 0 or cycle < 30 or any(n < 1 for n in cycles):
        raise SleepError("bad settings")
    w = parse(wake)
    return [
        {"cycles": n, "sleep_hours": round(n * cycle / 60, 2), "in_bed": fmt(w - n * cycle - latency)}
        for n in sorted(cycles, reverse=True)
    ]


def fixed_hours_check(bed: str, wake: str, hours: float, latency: int = 15, cycle: int = 90) -> dict[str, Any]:
    """Baseline: 'just sleep 8 hours'. Report where in a cycle the alarm lands."""
    asleep = (parse(wake) - parse(bed) - latency) % DAY
    into = asleep % cycle
    return {"asleep_minutes": asleep, "minutes_into_cycle": into, "mid_cycle": into != 0, "target_hours": hours}


def eight_hour_bed(wake: str, hours: float = 8.0) -> str:
    return fmt(parse(wake) - round(hours * 60))
