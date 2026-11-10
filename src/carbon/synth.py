"""Seeded generator for the synthetic household survey (CC0). Labels come from the transparent calculator."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from carbon.calculator import CATEGORIES, calculate
from carbon.schema import Answers

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "households.csv"


def _choice(rng: np.random.Generator, options: dict[str, float]) -> str:
    keys = list(options)
    return str(rng.choice(keys, p=np.array(list(options.values())) / sum(options.values())))


def generate(n: int = 3000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    for _ in range(n):
        size = int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.28, 0.34, 0.16, 0.16, 0.05, 0.01]))
        wealth = float(rng.lognormal(0, 0.3))  # hidden driver: it moves many answers together
        home = float(np.clip((35 + 22 * size) * wealth * rng.lognormal(0, 0.15), 22, 420))
        heating = _choice(
            rng, {"gas": 0.48, "electric": 0.14, "oil": 0.08, "heat_pump": 0.09, "district": 0.07, "wood": 0.14}
        )
        insulation = _choice(rng, {"poor": 0.25, "average": 0.5, "good": 0.25})
        thermostat = float(np.clip(round(rng.normal(20, 1.3)), 16, 24))
        green = bool(rng.random() < 0.25)
        mode = _choice(rng, {"car": 0.5, "bus_rail": 0.2, "mixed": 0.17, "bike_walk": 0.13})
        scale = size**0.5 * wealth**0.5
        car_base = {"car": 230, "mixed": 90, "bus_rail": 20, "bike_walk": 12}[mode]
        transit_base = {"car": 18, "mixed": 70, "bus_rail": 130, "bike_walk": 25}[mode]
        car_km = float(car_base * scale * rng.lognormal(0, 0.35))
        transit_km = float(transit_base * size**0.4 * rng.lognormal(0, 0.4))
        car_type = _choice(rng, {"petrol": 0.45, "diesel": 0.25, "hybrid": 0.16, "ev": 0.14})
        electricity = float((70 + 48 * size + 0.5 * home) * wealth * rng.lognormal(0, 0.22))
        short = int(rng.poisson(0.55 * wealth * size**0.5))
        long_ = int(rng.poisson(0.18 * wealth * size**0.5))
        diet = _choice(rng, {"meat_heavy": 0.2, "average": 0.42, "low_meat": 0.18, "vegetarian": 0.14, "vegan": 0.06})
        meat_free = int(rng.choice([0, 1, 2, 3], p=[0.6, 0.15, 0.15, 0.1])) if diet in ("average", "low_meat") else 0
        shopping = _choice(rng, {"low": 0.3, "average": 0.45, "high": 0.25})
        shop_mult = {"low": 0.6, "average": 1.0, "high": 1.7}[shopping]
        clothes = int(rng.poisson(7 * size**0.8 * shop_mult))
        recycling = _choice(rng, {"none": 0.1, "some": 0.5, "most": 0.4})
        waste = float(4.8 * size**0.85 * rng.lognormal(0, 0.25))
        answers = Answers(
            household_size=size,
            home_size_m2=round(home, 1),
            heating=heating,
            insulation=insulation,
            thermostat_c=thermostat,
            electricity_kwh_month=round(electricity, 1),
            green_tariff=green,
            commute_mode=mode,
            car_km_week=round(car_km, 1),
            car_type=car_type,
            transit_km_week=round(transit_km, 1),
            flights_short=short,
            flights_long=long_,
            diet=diet,
            meat_free_days=meat_free,
            shopping_level=shopping,
            clothes_items_year=clothes,
            recycling=recycling,
            waste_kg_week=round(waste, 1),
        )
        fp = calculate(answers)
        row: dict[str, object] = answers.model_dump()
        row["footprint_t"] = round(fp.total_t, 3)
        for cat in CATEGORIES:
            row[f"cat_{cat}_kg"] = round(fp.by_category_kg[cat], 1)
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the synthetic household survey CSV.")
    parser.add_argument("--n", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=DATA_PATH)
    args = parser.parse_args()
    df = generate(args.n, args.seed)
    df.to_csv(args.out, index=False)
    print(f"wrote {len(df)} households to {args.out}; median footprint {df.footprint_t.median():.1f} t")


if __name__ == "__main__":
    main()
