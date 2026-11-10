from __future__ import annotations

from fastapi.testclient import TestClient

from packlist.api import app


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Pack Weigh-In" in c.get("/").text
        assert len(c.get("/gear").json()) >= 40
        r = c.post("/pack", json={"days": 3, "min_temp_c": 2, "limit_kg": 12}).json()
        assert r["feasible"] and r["total_g"] <= r["limit_g"] and r["utility"] >= r["greedy_utility"]
        assert sum(r["by_category_g"].values()) == r["gear_g"]
        utils = [p["utility"] for p in r["curve"]]
        assert utils == sorted(utils) and len(utils) >= 4


def test_validation() -> None:
    with TestClient(app) as c:
        assert c.post("/pack", json={"days": 0}).status_code == 422
        assert c.post("/pack", json={"limit_kg": 100}).status_code == 422
        assert c.post("/pack", json={"rain_chance": -1}).status_code == 422
