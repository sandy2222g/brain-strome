"""Seeded synthetic listing generator for a made-up city (no real data, CC0)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from rentcheck.config import DATA_PATH, DISTRICTS, FEATURES, N_LISTINGS, SEED, TARGET


def generate(n: int = N_LISTINGS, seed: int = SEED) -> pd.DataFrame:
    """Draw ``n`` listings. Rent = size * district price * multiplicative effects * log-normal noise."""
    rng = np.random.default_rng(seed)
    names = list(DISTRICTS)
    # Central districts have more flats on the market.
    weights = np.array([1.2, 1.1, 1.3, 1.0, 1.1, 0.9, 0.8, 0.7])
    district = rng.choice(names, size=n, p=weights / weights.sum())
    base = np.array([DISTRICTS[d][0] for d in district])
    centre_mu = np.array([DISTRICTS[d][1] for d in district])
    metro_mu = np.array([DISTRICTS[d][2] for d in district])

    bedrooms = rng.choice([0, 1, 2, 3, 4], size=n, p=[0.08, 0.30, 0.34, 0.20, 0.08])
    size = np.clip(24 + bedrooms * 17 + rng.normal(0, 6, n), 18, 160).round().astype(int)
    bathrooms = np.clip(1 + (bedrooms >= 3) * rng.integers(0, 2, n) + (bedrooms >= 4), 1, 3)
    floor = rng.integers(0, 12, n)
    furnished = (rng.random(n) < 0.28).astype(int)
    balcony = (rng.random(n) < 0.45).astype(int)
    building_age = np.clip(rng.gamma(2.2, 14, n), 0, 120).round().astype(int)
    lift = (((floor >= 4) | (rng.random(n) < 0.25)) & (rng.random(n) < 0.9)).astype(int)
    dist_centre = np.clip(centre_mu * rng.lognormal(0, 0.25, n), 0.1, 15).round(2)
    dist_metro = np.clip(metro_mu * rng.lognormal(0, 0.35, n), 0.05, 5).round(2)
    pets = (rng.random(n) < 0.4).astype(int)

    # Per-m2 price: smaller flats cost more per m2; effects are multiplicative.
    ppm = base * (30 / np.maximum(size, 18)) ** 0.22
    mult = (
        1
        + 0.045 * np.minimum(floor, 8) * lift
        - 0.035 * np.minimum(floor, 3) * (1 - lift)
        + 0.09 * furnished
        + 0.05 * balcony
        + 0.04 * lift
        + 0.03 * (bathrooms - 1)
        + 0.03 * pets
        - 0.0030 * np.minimum(building_age, 80)
        + 0.0013 * np.maximum(building_age - 90, 0)
        - 0.012 * dist_centre
        - 0.045 * dist_metro
    )
    noise = rng.lognormal(0, 0.075, n)
    rent = (size * ppm * mult * noise / 5).round() * 5

    df = pd.DataFrame(
        {
            "district": district,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "size_m2": size,
            "floor": floor,
            "furnished": furnished,
            "balcony": balcony,
            "lift": lift,
            "building_age": building_age,
            "dist_centre_km": dist_centre,
            "dist_metro_km": dist_metro,
            "pets_allowed": pets,
            TARGET: rent.astype(int),
        }
    )
    df.insert(0, "id", np.arange(1, n + 1))
    return df[["id", *FEATURES, TARGET]]


def load_listings(path: Path = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def main() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(DATA_PATH, index=False)
    print(f"wrote {len(df)} listings to {DATA_PATH}")


if __name__ == "__main__":
    main()
