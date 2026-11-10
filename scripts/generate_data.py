"""Generate a synthetic clinic appointment dataset (no real patient data).

No-show probability follows a logistic model over plausible drivers (long lead time,
prior no-shows, no reminder, young age, distance...) plus noise. Run: python scripts/generate_data.py
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

SEED = 7
N = 6000
INSURANCE = ["public", "private", "none"]


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def make_row(rng: random.Random) -> dict[str, float | int | str]:
    age = int(min(95, max(1, rng.gauss(42, 20))))
    lead_days = int(min(90, max(0, rng.expovariate(1 / 14))))
    prior_visits = rng.randint(0, 20)
    prior_noshows = min(prior_visits, int(rng.random() ** 3 * 6))
    hour = rng.choice([8, 9, 10, 11, 13, 14, 15, 16, 17])
    weekday = rng.randint(0, 4)
    reminder = int(rng.random() < 0.7)
    distance = round(min(60, rng.expovariate(1 / 8)), 1)
    insurance = rng.choices(INSURANCE, weights=[0.35, 0.5, 0.15])[0]
    z = (
        -2.0
        + 0.035 * lead_days
        + 0.55 * prior_noshows
        - 0.9 * reminder
        + 0.02 * distance
        + (0.45 if age < 25 else 0.0)
        - (0.25 if age > 60 else 0.0)
        + (0.35 if hour in (8, 17) else 0.0)
        + (0.25 if weekday == 0 else 0.0)
        + {"public": 0.1, "private": -0.1, "none": 0.35}[insurance]
        - 0.04 * min(prior_visits - prior_noshows, 10)
        + rng.gauss(0, 0.4)
    )
    return {
        "age": age,
        "lead_days": lead_days,
        "prior_visits": prior_visits,
        "prior_noshows": prior_noshows,
        "hour": hour,
        "weekday": weekday,
        "reminder_sent": reminder,
        "distance_km": distance,
        "insurance": insurance,
        "no_show": int(rng.random() < sigmoid(z)),
    }


def main() -> None:
    rng = random.Random(SEED)
    rows = [make_row(rng) for _ in range(N)]
    out = Path(__file__).resolve().parents[1] / "data" / "appointments.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    rate = sum(int(r["no_show"]) for r in rows) / N
    print(f"wrote {N} rows to {out} (no-show rate {rate:.1%})")


if __name__ == "__main__":
    main()
