from __future__ import annotations

from fastapi.testclient import TestClient

from meetfair.api import app


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Same Time Zone" in c.get("/").text
        sample = c.get("/sample").json()
        best = c.post("/best", json=sample).json()
        assert len(best["slots"]) == 5
        rot = c.post("/rotation", json=sample).json()
        assert len(rot["weeks"]) == sample["weeks"] and rot["max_pain"] < rot["fixed_max_pain"]


def test_validation() -> None:
    with TestClient(app) as c:
        base = {
            "start_date": "2026-11-16",
            "people": [{"name": "A", "tz": "UTC"}, {"name": "B", "tz": "Europe/Berlin"}],
        }
        assert c.post("/best", json=base).status_code == 200
        assert c.post("/best", json={**base, "people": [{"name": "A", "tz": "UTC"}]}).status_code == 422
        assert (
            c.post(
                "/best", json={**base, "people": [{"name": "A", "tz": "UTC"}, {"name": "B", "tz": "Nowhere/Land"}]}
            ).status_code
            == 422
        )
        assert c.post("/best", json={**base, "duration_min": 20}).status_code == 422
        assert c.post("/rotation", json={**base, "weeks": 1}).status_code == 422


def test_bands_cover_the_day() -> None:
    with TestClient(app) as c:
        sample = c.get("/sample").json()
        b = c.post("/bands", json=sample).json()
        assert set(b) == {p["name"] for p in sample["people"]} and all(len(v) == 48 for v in b.values())
        assert c.post("/bands", json={**sample, "duration_min": 20}).status_code == 422
