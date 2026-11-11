"""Compare car park tariffs for a stay: hourly rate with a daily cap vs first-hour-dearer vs flat evening fee."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "carparks.json"


class ParkError(ValueError):
    """Invalid car park or stay."""


@dataclass(frozen=True)
class CarPark:
    name: str
    first_hour: float
    hourly: float
    daily_cap: float


def build(raw: list[dict]) -> list[CarPark]:  # type: ignore[type-arg]
    if not 1 <= len(raw) <= 20:
        raise ParkError("1-20 car parks")
    out = [CarPark(str(r["name"]), float(r["first_hour"]), float(r["hourly"]), float(r["daily_cap"])) for r in raw]
    if any(min(c.first_hour, c.hourly, c.daily_cap) <= 0 or c.daily_cap < c.first_hour for c in out):
        raise ParkError("prices must be positive and the daily cap at least the first hour")
    if len({c.name for c in out}) != len(out):
        raise ParkError("names must be unique")
    return out


def fee(c: CarPark, minutes: int) -> float:
    """Fee for a stay: first hour, then hourly (part hours round up), capped per 24 hours."""
    if not 1 <= minutes <= 7 * 24 * 60:
        raise ParkError("stay must be 1 minute to 7 days")
    total = 0.0
    for chunk in range(math.ceil(minutes / 1440)):
        m = min(1440, minutes - chunk * 1440)
        hours = math.ceil(m / 60)
        total += min(c.daily_cap, c.first_hour + max(0, hours - 1) * c.hourly)
    return round(total, 2)


def cheapest(cars: list[CarPark], minutes: int) -> tuple[str, dict[str, float]]:
    fees = {c.name: fee(c, minutes) for c in cars}
    return min(fees, key=lambda n: (fees[n], n)), fees


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
