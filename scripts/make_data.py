"""Generate a synthetic commute log: 120 working days of morning/evening trips with realistic spread."""

from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path


def base_minutes(hour: float, weekday: int) -> float:
    rush = math.exp(-((hour - 8.3) ** 2) / 1.2) + 0.8 * math.exp(-((hour - 17.5) ** 2) / 1.5)
    return 22 + 16 * rush - (3 if weekday == 4 else 0)


def make(days: int = 120, seed: int = 8) -> list[dict[str, str | float | int]]:
    rng = random.Random(seed)
    rows: list[dict[str, str | float | int]] = []
    d = date(2026, 1, 5)
    while len(rows) < days * 4:
        if d.weekday() < 5:
            for hour in (7.5, 8.25, 17.0, 17.75):
                h = hour + rng.uniform(-0.2, 0.2)
                t = base_minutes(h, d.weekday()) * math.exp(rng.gauss(0, 0.13))
                if rng.random() < 0.06:  # incident: breakdown or accident
                    t += rng.uniform(10, 35)
                rows.append(
                    {"date": d.isoformat(), "weekday": d.weekday(), "depart_hour": round(h, 2), "minutes": round(t, 1)}
                )
        d += timedelta(days=1)
    return rows


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "commutes.csv"
    rows = make()
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "weekday", "depart_hour", "minutes"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", out)
