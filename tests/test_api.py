from __future__ import annotations

from fastapi.testclient import TestClient

from seating.api import app


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Seating Chart Studio" in c.get("/").text
        party = c.get("/sample").json()
        r = c.post("/solve", json={**party, "seed": 4})
        assert r.status_code == 200
        sol = r.json()
        assert sol["violations"] == [] and sol["score"] > sol["random_baseline"]
        moved = [list(t) for t in sol["tables"]]
        moved[0][0], moved[1][0] = moved[1][0], moved[0][0]
        s2 = c.post("/score", json={**party, "tables": moved})
        assert s2.status_code == 200 and s2.json()["score"] != sol["score"]


def test_errors() -> None:
    with TestClient(app) as c:
        assert c.post("/solve", json={"guests": []}).status_code == 422
        dup = {"guests": [{"name": "A"}, {"name": "A"}]}
        assert c.post("/solve", json=dup).status_code == 422
        big = {"guests": [{"name": n} for n in "ABCDE"], "together": [list("ABCDE")], "table_size": 4}
        assert "must sit together" in c.post("/solve", json=big).json()["detail"]
        bad = {"guests": [{"name": "A"}, {"name": "B"}], "tables": [["A"]]}
        assert c.post("/score", json=bad).status_code == 422
