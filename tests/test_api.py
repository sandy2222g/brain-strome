from __future__ import annotations

from fastapi.testclient import TestClient

from buddies.api import app

A = {"name": "A", "skills": {"Calculus": 5}, "slots": ["Mon morning"]}
B = {"name": "B", "skills": {"Calculus": 0}, "slots": ["Mon morning"]}


def test_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Study Pass" in c.get("/").text
        sample = c.get("/sample").json()
        assert len(sample["students"]) == 28 and len(sample["subjects"]) == 6
        r = c.post("/match", json={"students": sample["students"], "seed": 1}).json()
        assert len(r["pairs"]) == 14 and r["total_score"] > r["random_baseline"]


def test_compatibility_endpoint() -> None:
    with TestClient(app) as c:
        r = c.post("/compatibility", json={"a": A, "b": B})
        assert r.status_code == 200 and r.json()["score"] > 5
        far = c.post("/compatibility", json={"a": A, "b": {**B, "slots": ["Tue evening"]}}).json()["score"]
        assert far < r.json()["score"]


def test_validation() -> None:
    with TestClient(app) as c:
        assert c.post("/match", json={"students": [A]}).status_code == 422
        assert c.post("/match", json={"students": [A, {**B, "name": "A"}]}).status_code == 422
        assert c.post("/match", json={"students": [A, {**B, "style": "loud"}]}).status_code == 422
        assert c.post("/match", json={"students": [A, {**B, "skills": {"Calculus": 9}}]}).status_code == 422
