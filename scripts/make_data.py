"""Generate 28 days of synthetic hourly household electricity use with labelled injected faults."""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

FAULTS = [
    # (day index, start hour, hours, extra kWh per hour, label)
    (17, 0, 8, 0.45, "fridge door left open"),
    (22, 10, 6, 1.6, "heater stuck on"),
    (25, 2, 5, 0.9, "oven left on"),
    (27, 14, 4, -0.9, "outage / everything off"),
]


def base(day: int, hour: int) -> float:
    weekend = day % 7 in (5, 6)
    morning = math.exp(-((hour - 7.5) ** 2) / 2.0) * (0.7 if weekend else 1.0)
    evening = math.exp(-((hour - 19.5) ** 2) / 3.0) * (1.4 if weekend else 1.1)
    daytime = (0.35 if weekend else 0.1) * math.exp(-((hour - 13) ** 2) / 12.0)
    return 0.25 + 0.7 * morning + 1.0 * evening + daytime


def make(days: int = 28, seed: int = 31) -> list[dict[str, str | float | int]]:
    rng = random.Random(seed)
    rows: list[dict[str, str | float | int]] = []
    for d in range(days):
        for h in range(24):
            kwh = max(0.05, base(d, h) + rng.gauss(0, 0.07))
            label = ""
            for fd, fh, n, extra, name in FAULTS:
                if d == fd and fh <= h < fh + n:
                    kwh = max(0.02, kwh + extra)
                    label = name
            rows.append({"day": d, "hour": h, "weekday": d % 7, "kwh": round(kwh, 3), "fault": label})
    return rows


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "usage.csv"
    rows = make()
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["day", "hour", "weekday", "kwh", "fault"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows")
