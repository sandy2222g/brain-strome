"""Solar position (NOAA low-precision formulas) and photographer-friendly light windows."""

from __future__ import annotations

import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "places.json"
# Sun-centre elevation (degrees) thresholds
SUNRISE = -0.833  # upper limb on the horizon, with refraction
GOLDEN_TOP = 6.0  # golden hour: from the horizon event up to 6 degrees
BLUE_BOTTOM = -6.0  # civil twilight ends; blue hour is roughly -6 to -4 degrees
BLUE_TOP = -4.0


class SunError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def sun_declination_eqtime(unix_s: float) -> tuple[float, float]:
    """Return (solar declination in radians, equation of time in minutes)."""
    jd = unix_s / 86400.0 + 2440587.5
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360
    m = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    c = (
        math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t))
        + math.sin(2 * m) * (0.019993 - 0.000101 * t)
        + math.sin(3 * m) * 0.000289
    )
    omega = math.radians(125.04 - 1934.136 * t)
    lam = math.radians(l0 + c - 0.00569 - 0.00478 * math.sin(omega))
    eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60
    eps = math.radians(eps0 + 0.00256 * math.cos(omega))
    decl = math.asin(math.sin(eps) * math.sin(lam))
    y = math.tan(eps / 2) ** 2
    l0r = math.radians(l0)
    eqt = 4 * math.degrees(
        y * math.sin(2 * l0r)
        - 2 * e * math.sin(m)
        + 4 * e * y * math.sin(m) * math.cos(2 * l0r)
        - 0.5 * y * y * math.sin(4 * l0r)
        - 1.25 * e * e * math.sin(2 * m)
    )
    return decl, eqt


def elevation(unix_s: float, lat: float, lon: float) -> float:
    """Sun-centre elevation above the horizon in degrees."""
    decl, eqt = sun_declination_eqtime(unix_s)
    utc_min = (unix_s % 86400) / 60.0
    hour_angle = math.radians((utc_min + eqt + 4 * lon) / 4.0 - 180.0)
    phi = math.radians(lat)
    s = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(hour_angle)
    return math.degrees(math.asin(max(-1.0, min(1.0, s))))


def _crossings(day_start: float, lat: float, lon: float, level: float) -> tuple[float | None, float | None]:
    """First rising crossing of `level` from day_start, and the first falling crossing after it.

    The scan covers 36 h so a sunset just after midnight (high latitudes) still belongs to the day it follows.
    """
    rise = fall = None
    prev = elevation(day_start, lat, lon) - level
    for minute in range(1, 2161):
        t = day_start + minute * 60
        cur = elevation(t, lat, lon) - level
        if prev < 0 <= cur and rise is None:
            rise = _refine(t - 60, t, lat, lon, level)
        elif prev >= 0 > cur and rise is not None and fall is None:
            fall = _refine(t - 60, t, lat, lon, level)
        prev = cur
    return rise, fall


def _refine(lo: float, hi: float, lat: float, lon: float, level: float) -> float:
    sign_lo = elevation(lo, lat, lon) - level < 0
    for _ in range(20):
        mid = (lo + hi) / 2
        if (elevation(mid, lat, lon) - level < 0) == sign_lo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _hhmm(unix_s: float | None, tz: float, day_start: float = 0.0) -> str | None:
    if unix_s is None:
        return None
    local = datetime.fromtimestamp(unix_s, UTC) + timedelta(hours=tz)
    text = (local + timedelta(seconds=30)).strftime("%H:%M")
    return text + " (+1)" if day_start and unix_s - day_start >= 86400 else text


def plan(day: str, lat: float, lon: float, tz: float) -> dict[str, Any]:
    """Sunrise, sunset, golden-hour and blue-hour windows for one local calendar day."""
    try:
        d = date.fromisoformat(day)
    except ValueError as err:
        raise SunError("date must look like 2026-06-21") from err
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and -14 <= tz <= 14):
        raise SunError("latitude, longitude or time zone out of range")
    start = datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp() - tz * 3600
    rise, fall = _crossings(start, lat, lon, SUNRISE)
    g_up, g_down = _crossings(start, lat, lon, GOLDEN_TOP)
    dawn_blue_start, dusk_blue_end = _crossings(start, lat, lon, BLUE_BOTTOM)
    dawn_blue_end, dusk_blue_start = _crossings(start, lat, lon, BLUE_TOP)

    def t(x: float | None) -> str | None:
        return _hhmm(x, tz, start)

    noon = max(range(1441), key=lambda m: elevation(start + m * 60, lat, lon))
    peak = elevation(start + noon * 60, lat, lon)
    status = "normal" if rise and fall else ("polar day" if peak > SUNRISE else "polar night")
    return {
        "date": day,
        "status": status,
        "sunrise": t(rise),
        "sunset": t(fall),
        "morning_golden": [t(rise), t(g_up)] if all([rise, g_up]) else None,
        "evening_golden": [t(g_down), t(fall)] if all([g_down, fall]) else None,
        "morning_blue": [t(dawn_blue_start), t(dawn_blue_end)] if all([dawn_blue_start, dawn_blue_end]) else None,
        "evening_blue": [t(dusk_blue_start), t(dusk_blue_end)] if all([dusk_blue_start, dusk_blue_end]) else None,
        "solar_noon": t(start + noon * 60),
        "max_elevation": round(peak, 1),
        "daylight_minutes": round((fall - rise) / 60) if rise and fall else None,
    }


def rule_of_thumb(day: str, lat: float, lon: float, tz: float) -> dict[str, Any]:
    """Baseline: assume sunrise 06:00 and sunset 18:00 everywhere, and report the error against the real times."""
    real = plan(day, lat, lon, tz)
    if real["sunrise"] is None or real["sunset"] is None:
        return {"sunrise": "06:00", "sunset": "18:00", "sunrise_error_min": None, "sunset_error_min": None}

    def mins(s: str) -> int:
        h, m = s.split(":")
        return int(h) * 60 + int(m)

    return {
        "sunrise": "06:00",
        "sunset": "18:00",
        "sunrise_error_min": abs(mins(real["sunrise"]) - 360),
        "sunset_error_min": abs(mins(real["sunset"]) - 1080),
    }
