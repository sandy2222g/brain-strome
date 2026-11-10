from __future__ import annotations

from pathlib import Path

import pytest

from noshow.model import NoShowModel, load_dataset

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def dataset():  # type: ignore[no-untyped-def]
    return load_dataset(ROOT / "data" / "appointments.csv")


@pytest.fixture(scope="session")
def model(dataset) -> NoShowModel:  # type: ignore[no-untyped-def]
    m = NoShowModel()
    m.fit(dataset)
    return m


RISKY = {"age": 20, "lead_days": 60, "prior_visits": 5, "prior_noshows": 4, "hour": 8, "weekday": 0,
         "reminder_sent": 0, "distance_km": 30.0, "insurance": "none"}
SAFE = {"age": 55, "lead_days": 1, "prior_visits": 15, "prior_noshows": 0, "hour": 11, "weekday": 3,
        "reminder_sent": 1, "distance_km": 2.0, "insurance": "private"}
