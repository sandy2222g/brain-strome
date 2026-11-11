"""Day-by-day sleep-shift plan for a long-haul flight.

Rule of thumb used here (a planning heuristic, not medical advice): the body clock moves about
1.0 h/day earlier (eastward travel) or 1.5 h/day later (westward travel). We shift gradually
before departure (up to `pre_days`), then keep shifting after arrival until the body clock matches
local time. The shorter way around the clock is always used (a +14 h shift is really -10 h).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

EAST_RATE = 1.0
WEST_RATE = 1.5


class TripError(ValueError):
    """Invalid trip."""


@dataclass(frozen=True)
class Day:
    day: date
    label: str
    shift_done: float
    bedtime: str
    wake: str
    bedtime_dest: str
    wake_dest: str
    light: str


def zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as err:
        raise TripError(f"unknown time zone: {name}") from err


def hour_shift(origin: str, dest: str, on: date) -> float:
    """Signed hours the clock must move to match the destination, in (-12, 12].

    Positive = destination is ahead (eastward, body clock must advance earlier). We use the shorter way.
    """
    noon = datetime(on.year, on.month, on.day, 12)
    o = noon.replace(tzinfo=zone(origin)).utcoffset()
    d = noon.replace(tzinfo=zone(dest)).utcoffset()
    assert o is not None and d is not None
    diff = (d - o).total_seconds() / 3600
    while diff > 12:
        diff -= 24
    while diff <= -12:
        diff += 24
    return diff


def fmt(hours: float) -> str:
    m = round((hours % 24) * 60)
    return f"{m // 60 % 24:02d}:{m % 60:02d}"


def plan(
    origin: str,
    dest: str,
    flight_day: date,
    bed: float = 23.0,
    wake: float = 7.0,
    pre_days: int = 3,
) -> dict[str, object]:
    """Return the shift summary and a list of daily rows from `pre_days` before to arrival + needed days."""
    if not 0 <= pre_days <= 7:
        raise TripError("pre_days must be 0-7")
    if not (0 <= bed < 24 and 0 <= wake < 24):
        raise TripError("bed and wake must be hours 0-24")
    shift = hour_shift(origin, dest, flight_day)
    rate = EAST_RATE if shift > 0 else WEST_RATE
    direction = "east" if shift > 0 else "west" if shift < 0 else "none"
    total = abs(shift)
    days_needed = int(-(-total // rate)) if total else 0
    rows: list[Day] = []
    start = flight_day - timedelta(days=pre_days)
    n_days = max(pre_days + 1, days_needed)
    for i in range(n_days):
        d = start + timedelta(days=i)
        if i < pre_days:
            label = f"Pre-shift {i + 1}/{pre_days}"
        elif i == pre_days:
            label = "Flight day"
        else:
            label = f"Day {i - pre_days} at destination"
        done = min(total, rate * (i + 1))
        sign = 1 if shift > 0 else -1
        # While still at home, times are in origin clock; the body-clock target moves toward destination.
        offset = sign * done
        b, w = bed - offset, wake - offset
        bd, wd = b + shift, w + shift  # the same moments on the destination clock
        if shift > 0:
            light = f"light (dest. clock): bright after {fmt(wd)}, avoid after {fmt(bd - 3)}"
        elif shift < 0:
            light = f"light (dest. clock): bright {fmt(bd - 4)}-{fmt(bd - 1)}, dim before {fmt(wd)}"
        else:
            light = "no shift needed"
        rows.append(Day(d, label, round(done, 2), fmt(b), fmt(w), fmt(b + shift), fmt(w + shift), light))
    return {
        "shift_hours": shift,
        "direction": direction,
        "rate_per_day": rate,
        "days_to_adjust": days_needed,
        "days": [r.__dict__ | {"day": r.day.isoformat()} for r in rows],
    }
