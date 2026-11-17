"""Moon phases from orbital formulas (Meeus, 'Astronomical Algorithms'), checked against real full moons."""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "full_moons_2024.json"
SYNODIC = 29.530588861  # mean days between new moons
J2000_NEW_MOON = 2451550.09766  # a known new moon, Julian date (2000-01-06)
UNIX_EPOCH_JD = 2440587.5
NAMES = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous", "Full moon", "Waning gibbous",
         "Last quarter", "Waning crescent"]


class MoonError(ValueError):
    pass


def to_jd(t: datetime) -> float:
    return (t - datetime(1970, 1, 1)).total_seconds() / 86400 + UNIX_EPOCH_JD


def from_jd(jd: float) -> datetime:
    return datetime(1970, 1, 1) + timedelta(days=jd - UNIX_EPOCH_JD)


def phase_event_jd(k: float, corrected: bool = True) -> float:
    """Julian date of a new moon (k whole) or full moon (k + 0.5): mean time, plus the main wobble terms."""
    jd = J2000_NEW_MOON + SYNODIC * k
    if not corrected:
        return jd
    t = k / 1236.85
    e = 1 - 0.002516 * t
    m = math.radians((2.5534 + 29.10535670 * k) % 360)  # sun's mean anomaly
    mp = math.radians((201.5643 + 385.81693528 * k) % 360)  # moon's mean anomaly
    if abs(k - round(k)) < 0.25:  # new moon
        return jd - 0.40720 * math.sin(mp) + 0.17241 * e * math.sin(m) + 0.01608 * math.sin(2 * mp)
    return jd - 0.40614 * math.sin(mp) + 0.17302 * e * math.sin(m) + 0.01614 * math.sin(2 * mp)


def full_moons_in(year: int, corrected: bool = True) -> list[datetime]:
    k0 = math.floor((year - 2000) * 12.3685) - 2
    out = []
    for i in range(20):
        t = from_jd(phase_event_jd(k0 + i + 0.5, corrected))
        if t.year == year:
            out.append(t)
    return out


def _cycle(t: datetime) -> tuple[float, float]:
    """(age, length) of the current lunation, from the real (corrected) new moons on each side."""
    jd = to_jd(t)
    k = math.floor((jd - J2000_NEW_MOON) / SYNODIC)
    news = [phase_event_jd(k + i) for i in range(-1, 3)]
    prev = max(n for n in news if n <= jd)
    nxt = min(n for n in news if n > jd)
    return jd - prev, nxt - prev


def age_days(t: datetime) -> float:
    """Days since the last new moon."""
    return _cycle(t)[0]


def illumination(t: datetime) -> float:
    age, length = _cycle(t)
    return (1 - math.cos(2 * math.pi * age / length)) / 2


def phase_name(t: datetime) -> str:
    age, length = _cycle(t)
    return NAMES[int(age / length * 8 + 0.5) % 8]


def month_calendar(year: int, month: int) -> list[dict[str, object]]:
    if not 1900 <= year <= 2100 or not 1 <= month <= 12:
        raise MoonError("year must be 1900-2100 and month 1-12")
    d = datetime(year, month, 1, 12)
    out = []
    while d.month == month:
        out.append({"day": d.day, "illumination": round(illumination(d), 3), "phase": phase_name(d),
                    "age": round(age_days(d), 1)})
        d += timedelta(days=1)
    return out


def reference() -> list[datetime]:
    return [datetime.fromisoformat(s) for s in json.loads(DATA.read_text())["full_moons"]]


def error_hours(corrected: bool) -> list[float]:
    ref = reference()
    got = full_moons_in(2024, corrected)
    if len(got) != len(ref):
        raise MoonError("model and reference disagree on the number of full moons")
    return [abs((g - r).total_seconds()) / 3600 for g, r in zip(got, ref, strict=True)]
