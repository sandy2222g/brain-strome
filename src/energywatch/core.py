"""Seasonal robust anomaly detector for hourly household electricity use.

Baseline: for each (weekday-type, hour) slot take the median of the training days and a robust spread
(MAD scaled to a standard deviation). Score = (reading - median) / spread. An *alert* needs `min_run`
consecutive hours beyond the threshold (two-sided), so one noisy hour does not raise an alarm. The
naive comparison flags any reading more than 3 standard deviations from the overall mean.
"""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "usage.csv"
MAD_SCALE = 1.4826
MIN_SPREAD = 0.05


class UsageError(ValueError):
    """Invalid data."""


@dataclass(frozen=True)
class Reading:
    day: int
    hour: int
    weekday: int
    kwh: float
    fault: str = ""


@dataclass(frozen=True)
class Alert:
    day: int
    start: int
    hours: int
    peak_score: float
    direction: str


def load(path: Path = DATA) -> list[Reading]:
    with path.open() as f:
        return [
            Reading(int(r["day"]), int(r["hour"]), int(r["weekday"]), float(r["kwh"]), r["fault"])
            for r in csv.DictReader(f)
        ]


def slot(r: Reading) -> tuple[bool, int]:
    return (r.weekday >= 5, r.hour)


def fit(train: list[Reading]) -> dict[tuple[bool, int], tuple[float, float]]:
    if not train:
        raise UsageError("no training data")
    groups: dict[tuple[bool, int], list[float]] = {}
    for r in train:
        groups.setdefault(slot(r), []).append(r.kwh)
    model = {}
    for k, v in groups.items():
        med = statistics.median(v)
        mad = statistics.median(abs(x - med) for x in v)
        model[k] = (med, max(MAD_SCALE * mad, MIN_SPREAD))
    return model


def score(model: dict[tuple[bool, int], tuple[float, float]], r: Reading) -> float:
    if slot(r) not in model:
        raise UsageError(f"no baseline for slot {slot(r)}")
    med, spread = model[slot(r)]
    return (r.kwh - med) / spread


def alerts(
    model: dict[tuple[bool, int], tuple[float, float]],
    readings: list[Reading],
    threshold: float = 4.0,
    min_run: int = 2,
) -> list[Alert]:
    """Runs of >= min_run consecutive hours whose score has the same sign and magnitude > threshold."""
    out: list[Alert] = []
    run: list[tuple[Reading, float]] = []

    def flush() -> None:
        if len(run) >= min_run:
            peak = max(run, key=lambda t: abs(t[1]))[1]
            out.append(Alert(run[0][0].day, run[0][0].hour, len(run), round(peak, 1), "high" if peak > 0 else "low"))
        run.clear()

    for r in readings:
        s = score(model, r)
        same = (
            bool(run)
            and (run[-1][1] > 0) == (s > 0)
            and r.day * 24 + r.hour == run[-1][0].day * 24 + run[-1][0].hour + 1
        )
        if abs(s) > threshold:
            if run and not same:
                flush()
            run.append((r, s))
        else:
            flush()
    flush()
    return out


def naive_alerts(train: list[Reading], readings: list[Reading], sigma: float = 3.0) -> list[Alert]:
    vals = [r.kwh for r in train]
    mu, sd = statistics.fmean(vals), statistics.pstdev(vals)
    return [
        Alert(r.day, r.hour, 1, round((r.kwh - mu) / sd, 1), "high" if r.kwh > mu else "low")
        for r in readings
        if abs(r.kwh - mu) > sigma * sd
    ]


def evaluate(readings: list[Reading], found: list[Alert]) -> dict[str, float]:
    """Fault-level recall and false alarms: an alert is true if it overlaps any labelled fault hour."""
    faulty = {(r.day, r.hour) for r in readings if r.fault}
    fault_days = {(r.day, r.fault) for r in readings if r.fault}
    hit_faults, false_alarms = set(), 0
    for a in found:
        hours = {(a.day, a.start + i) for i in range(a.hours)}
        if hours & faulty:
            hit_faults.update((r.day, r.fault) for r in readings if r.fault and (r.day, r.hour) in hours)
        else:
            false_alarms += 1
    return {
        "faults": len(fault_days),
        "faults_caught": len(hit_faults),
        "false_alarms": false_alarms,
        "alerts": len(found),
    }
