from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from pantry import api

ITEMS = [
    {"name": "spinach", "expiry": "2026-01-13"},
    {"name": "Eggs", "expiry": "2026-01-25", "quantity": 6},
    {"name": "butter", "expiry": "2026-01-30"},
    {"name": "lettuce", "expiry": "2026-01-10"},
]
BASE = {"items": ITEMS, "household_size": 2, "today": "2026-01-12"}


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    api.MODEL_PATH = tmp_path_factory.mktemp("models") / "waste.joblib"
    with TestClient(api.app) as c:
        yield c


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_metrics(client: TestClient) -> None:
    m = client.get("/metrics").json()
    assert m["waste_model"]["data"] == "synthetic"
    assert m["waste_model"]["roc_auc"] > 0.8
    assert m["recipes"] >= 60


def test_prioritize(client: TestClient) -> None:
    body = client.post("/prioritize", json=BASE).json()
    names = [i["name"] for i in body["items"]]
    assert names[0] == "spinach" and names[-1] == "lettuce"
    assert body["items"][-1]["status"] == "expired"
    assert body["items"][0]["days_left"] == 1


def test_recipes(client: TestClient) -> None:
    body = client.post("/recipes", json={**BASE, "limit": 3}).json()
    assert body["recipes"][0]["name"] == "Spinach and Egg Scramble"
    assert body["best_waste_kg"] > 0 and body["best_waste_value"] > 0


def test_plan(client: TestClient) -> None:
    body = client.post("/plan", json={**BASE, "days": 5}).json()
    assert len(body["days"]) == 5
    assert body["days"][0]["recipe"] is not None
    assert body["waste_kg"] > 0


def test_sample_round_trips(client: TestClient) -> None:
    sample = client.get("/sample").json()
    res = client.post("/recipes", json=sample)
    assert res.status_code == 200
    assert res.json()["recipes"]


def test_validation(client: TestClient) -> None:
    assert client.post("/prioritize", json={"items": []}).status_code == 422
    assert client.post("/prioritize", json={"items": [{"name": "x", "quantity": -1}]}).status_code == 422
    assert client.post("/plan", json={**BASE, "days": 30}).status_code == 422


def test_index_served(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "Pantry Saver" in r.text
