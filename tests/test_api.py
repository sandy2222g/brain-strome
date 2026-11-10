from __future__ import annotations

from fastapi.testclient import TestClient

from plantparent.api import app


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Plant Parent" in c.get("/").text
        assert "test_mae_days" in c.get("/metrics").json()
        assert len(c.get("/species").json()) >= 20
        sample = c.get("/sample").json()
        r = c.post("/schedule", json=sample)
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == len(sample["plants"]) and body["calendar"] and body["pet_warnings"]
        fb = c.post("/feedback", json={"multiplier": 1.0, "soil": "wet"}).json()
        assert fb["multiplier"] > 1.0


def test_validation() -> None:
    with TestClient(app) as c:
        base = {"name": "X", "species": "Monstera", "pot_cm": 15, "material": "plastic", "last_watered": "2026-06-01"}
        assert c.post("/schedule", json={"plants": []}).status_code == 422
        assert c.post("/schedule", json={"plants": [{**base, "species": "Triffid"}]}).status_code == 422
        assert c.post("/schedule", json={"plants": [{**base, "material": "glass"}]}).status_code == 422
        assert c.post("/schedule", json={"plants": [{**base, "pot_cm": 1}]}).status_code == 422
        assert c.post("/feedback", json={"soil": "soggy"}).status_code == 422
        assert c.post("/schedule", json={"plants": [base], "today": "2026-06-10"}).status_code == 200
