"""Current and longest streaks from check-in dates, with an allowed number of missed days in a row."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "habit.json"


class StreakError(ValueError):
    """Raised for invalid dates or settings."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def parse_days(raw: list[str]) -> list[date]:
    try:
        return sorted({date.fromisoformat(s) for s in raw})
    except ValueError as err:
        raise StreakError(f"bad date: {err}") from err


def runs(days: list[date], grace: int) -> list[tuple[date, date, int]]:
    """Runs of check-ins where consecutive check-ins are at most `grace + 1` days apart.

    Returns (first, last, number of check-ins).
    """
    if grace < 0:
        raise StreakError("grace_days cannot be negative")
    out: list[tuple[date, date, int]] = []
    for d in days:
        if out and (d - out[-1][1]).days <= grace + 1:
            first, _, n = out[-1]
            out[-1] = (first, d, n + 1)
        else:
            out.append((d, d, 1))
    return out


def summary(raw: list[str], today: date, grace: int = 1) -> dict[str, Any]:
    days = parse_days(raw)
    if not days:
        raise StreakError("need at least one check-in")
    if days[-1] > today:
        raise StreakError("check-in dated after today")
    rs = runs(days, grace)
    first, last, n = rs[-1]
    alive = (today - last).days <= grace + 1
    longest = max(rs, key=lambda r: (r[2], r[1]))
    return {
        "current": n if alive else 0,
        "current_since": first.isoformat() if alive else None,
        "longest": longest[2],
        "longest_span": [longest[0].isoformat(), longest[1].isoformat()],
        "total_checkins": len(days),
        "last_checkin": last.isoformat(),
        "alive": alive,
    }


def strict_summary(raw: list[str], today: date) -> dict[str, Any]:
    """Baseline: a single missed day resets the streak to zero."""
    return summary(raw, today, grace=0)


def heatmap(raw: list[str], today: date, weeks: int = 9) -> list[list[str]]:
    """Grid of 'done' / 'miss' / 'future' cells, one row per week ending on the week of `today` (Mon-first)."""
    days = set(parse_days(raw))
    monday = today - timedelta(days=today.weekday())
    grid = []
    for w in range(weeks - 1, -1, -1):
        row = []
        for i in range(7):
            x = monday - timedelta(weeks=w) + timedelta(days=i)
            row.append("future" if x > today else "done" if x in days else "miss")
        grid.append(row)
    return grid
