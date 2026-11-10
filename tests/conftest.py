from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from carbon.model import CarbonModel, load_dataset  # noqa: E402
from carbon.schema import Answers  # noqa: E402


def make_answers(**overrides: object) -> Answers:
    """A small, easy-to-compute household: two people, 100 m2 gas home, everything answered."""
    base: dict[str, object] = {
        "household_size": 2,
        "home_size_m2": 100,
        "heating": "gas",
        "insulation": "average",
        "thermostat_c": 20,
        "electricity_kwh_month": 300,
        "green_tariff": False,
        "commute_mode": "car",
        "car_km_week": 100,
        "car_type": "petrol",
        "transit_km_week": 50,
        "flights_short": 2,
        "flights_long": 1,
        "diet": "average",
        "meat_free_days": 0,
        "shopping_level": "average",
        "clothes_items_year": 10,
        "recycling": "some",
        "waste_kg_week": 10,
    }
    base.update(overrides)
    return Answers(**base)  # type: ignore[arg-type]


@pytest.fixture(scope="session")
def model() -> CarbonModel:
    return CarbonModel().fit(load_dataset(ROOT / "data" / "households.csv"))
