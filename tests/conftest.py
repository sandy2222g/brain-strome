from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from rentcheck import api as api_module
from rentcheck.config import DATA_PATH
from rentcheck.data import load_listings
from rentcheck.model import RentModel

FLAT: dict[str, Any] = {
    "district": "Linden Park",
    "bedrooms": 2,
    "bathrooms": 1,
    "size_m2": 58,
    "floor": 3,
    "furnished": 0,
    "balcony": 1,
    "lift": 1,
    "building_age": 22,
    "dist_centre_km": 2.6,
    "dist_metro_km": 0.6,
    "pets_allowed": 1,
}


@pytest.fixture(scope="session")
def listings():  # type: ignore[no-untyped-def]
    return load_listings(DATA_PATH)


@pytest.fixture(scope="session")
def model(listings) -> RentModel:  # type: ignore[no-untyped-def]
    return RentModel().fit(listings)


@pytest.fixture(scope="session")
def client(model: RentModel) -> TestClient:
    api_module.get_model.cache_clear()
    api_module.get_model = lambda: model  # type: ignore[assignment]
    return TestClient(api_module.app)


@pytest.fixture()
def flat() -> dict[str, Any]:
    return dict(FLAT)
