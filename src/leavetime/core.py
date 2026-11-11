"""Pick a departure time that meets an on-time confidence target.

Travel times are modelled per departure-time bucket with *empirical quantiles* (no distribution
assumption). Calibration is checked on a later, held-out period; no extra margin is added, so
out-of-sample coverage runs a little under the target (see the README).
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "commutes.csv"
BUCKET = 0.5  # hours


class LeaveError(ValueError):
    """Invalid request or not enough data."""


@dataclass(frozen=True)
class Trip:
    weekday: int
    hour: float
    minutes: float


def load(path: Path = DATA) -> list[Trip]:
    with path.open() as f:
        return [Trip(int(r["weekday"]), float(r["depart_hour"]), float(r["minutes"])) for r in csv.DictReader(f)]


def bucket(hour: float) -> int:
    return math.floor(hour / BUCKET)


def quantile(values: list[float], q: float) -> float:
    """Empirical quantile with the conservative 'higher' rule (never under-promises)."""
    if not values:
        raise LeaveError("no data")
    if not 0 < q < 1:
        raise LeaveError("confidence must be between 0 and 1")
    s = sorted(values)
    return s[min(len(s) - 1, math.ceil(q * len(s)) - 1)]


def times_for(trips: list[Trip], hour: float, min_n: int = 15) -> list[float]:
    """Trip durations from the departure bucket, widening to neighbours until min_n samples."""
    b, width = bucket(hour), 0
    while True:
        got = [t.minutes for t in trips if abs(bucket(t.hour) - b) <= width]
        if len(got) >= min_n or width > 6:
            break
        width += 1
    if len(got) < min_n:
        raise LeaveError("not enough history near that departure time")
    return got


def predict_minutes(trips: list[Trip], hour: float, confidence: float) -> float:
    return quantile(times_for(trips, hour), confidence)


def leave_by(trips: list[Trip], arrive_hour: float, confidence: float, step: float = 1 / 12) -> dict[str, float]:
    """Latest departure (hours) such that depart + predicted duration <= arrive_hour at `confidence`."""
    h = arrive_hour - 0.2
    while h > arrive_hour - 3:
        need = predict_minutes(trips, h, confidence) / 60
        if h + need <= arrive_hour:
            return {"leave_hour": round(h, 3), "minutes_needed": round(need * 60, 1)}
        h -= step
    raise LeaveError("cannot arrive on time within a 3-hour window")


def hhmm(hour: float) -> str:
    m = round(hour * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def on_time_rate(train: list[Trip], test: list[Trip], confidence: float) -> float:
    """Share of held-out trips that would have arrived within the predicted time (calibration check)."""
    ok = sum(1 for t in test if t.minutes <= predict_minutes(train, t.hour, confidence))
    return ok / len(test)


def fixed_buffer_rate(train: list[Trip], test: list[Trip], buffer: float = 1.2) -> float:
    """Baseline: assume the average trip times a flat 20% buffer."""
    mean = sum(t.minutes for t in train) / len(train)
    return sum(1 for t in test if t.minutes <= mean * buffer) / len(test)


def split(trips: list[Trip], frac: float = 0.75) -> tuple[list[Trip], list[Trip]]:
    """Chronological split (log is date-ordered) so test data is strictly later than train data."""
    k = int(len(trips) * frac)
    return trips[:k], trips[k:]
