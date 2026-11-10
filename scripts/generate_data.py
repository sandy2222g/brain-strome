"""Generate synthetic study-habit data for the score model (no real students)."""
from __future__ import annotations

import csv
import random
from pathlib import Path

N = 1500
SEED = 11


def row(rng: random.Random) -> dict[str, float | int]:
    total_hours = round(rng.uniform(5, 80), 1)
    n_sessions = max(2, int(total_hours / rng.uniform(0.6, 2.5)))
    spacing_days = round(rng.uniform(0, 7), 1)  # average gap between reviews of one topic
    difficulty = round(rng.random(), 2)
    prior_confidence = round(rng.random(), 2)
    sleep_hours = round(min(10, max(4, rng.gauss(7, 1.2))), 1)
    spacing_gain = 8 * min(spacing_days, 4) / 4 - 3 * max(spacing_days - 5, 0) / 2  # cramming hurts, huge gaps too
    score = (
        20
        + 22 * prior_confidence
        + 9 * (1 - 2.718 ** (-total_hours / 25)) * 4
        + spacing_gain
        - 14 * difficulty
        + 2.2 * (sleep_hours - 6)
        + rng.gauss(0, 4)
    )
    return {
        "total_hours": total_hours,
        "n_sessions": n_sessions,
        "spacing_days": spacing_days,
        "difficulty": difficulty,
        "prior_confidence": prior_confidence,
        "sleep_hours": sleep_hours,
        "score": round(min(100, max(0, score)), 1),
    }


def main() -> None:
    rng = random.Random(SEED)
    rows = [row(rng) for _ in range(N)]
    out = Path(__file__).resolve().parents[1] / "data" / "study_sessions.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {N} rows to {out}")


if __name__ == "__main__":
    main()
