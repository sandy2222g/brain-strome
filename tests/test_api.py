from __future__ import annotations

from fastapi.testclient import TestClient

from arcmix.api import app


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Arc Mixer" in c.get("/").text
        assert "Slow burn" in c.get("/arcs").json() and sum(c.get("/moods").json().values()) == 200
        assert len(c.get("/tracks", params={"limit": 5}).json()) == 5
        r = c.post("/build", json={"arc": "Slow burn", "minutes": 30}).json()
        assert r["tracks"] and r["arc_rmse"] < r["baseline_arc_rmse"] and len(r["arc"]) == 41
        starts = [t["start_s"] for t in r["tracks"]]
        assert starts == sorted(starts) and starts[0] == 0


def test_custom_points_and_validation() -> None:
    with TestClient(app) as c:
        ok = c.post("/build", json={"points": [[0, 0.3], [0.5, 0.9], [1, 0.3]], "minutes": 25})
        assert ok.status_code == 200
        assert c.post("/build", json={"arc": "Nope"}).status_code == 422
        assert c.post("/build", json={"minutes": 2}).status_code == 422
        assert c.post("/build", json={"points": [[0, 2], [1, 0.5]]}).status_code == 422
        assert c.post("/build", json={"moods": ["Calm"], "minutes": 200}).status_code == 422
