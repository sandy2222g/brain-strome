from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import RISKY, SAFE
from noshow.api import app


def test_health_index_metrics() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "No-Show" in c.get("/").text
        assert "test_auc" in c.get("/metrics").json()


def test_predict() -> None:
    with TestClient(app) as c:
        r = c.post("/predict", json=RISKY)
        assert r.status_code == 200
        assert 0 < r.json()["probability"] < 1


def test_predict_validation() -> None:
    with TestClient(app) as c:
        assert c.post("/predict", json={**RISKY, "insurance": "gold"}).status_code == 422
        assert c.post("/predict", json={**RISKY, "age": -1}).status_code == 422
        assert c.post("/predict", json={"age": 3}).status_code == 422


def test_plan_day_and_sample() -> None:
    with TestClient(app) as c:
        r = c.post("/plan-day", json={"appointments": [SAFE, RISKY]})
        assert r.status_code == 200 and r.json()["items"][0]["probability"] >= r.json()["items"][1]["probability"]
        sample = c.get("/sample-day").json()
        assert len(sample["appointments"]) == 20
        assert c.post("/plan-day", json=sample).json()["appointments"] == 20
        assert c.post("/plan-day", json={"appointments": []}).status_code == 422
