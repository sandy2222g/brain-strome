from __future__ import annotations

from fastapi.testclient import TestClient

from triage.api import app


def client() -> TestClient:
    return TestClient(app)


def test_health_and_index() -> None:
    with client() as c:
        assert c.get("/health").json() == {"status": "ok"}
        r = c.get("/")
        assert r.status_code == 200 and "Support Ticket Triage" in r.text


def test_predict_ok() -> None:
    with client() as c:
        r = c.post("/predict", json={"subject": "refund", "body": "I was charged twice, refund please"})
        assert r.status_code == 200
        data = r.json()
        assert data["category"] == "billing"
        assert data["priority"] in {"low", "medium", "high", "urgent"}


def test_predict_validation() -> None:
    with client() as c:
        assert c.post("/predict", json={"subject": "x", "body": ""}).status_code == 422
        assert c.post("/predict", json={}).status_code == 422


def test_metrics_endpoint() -> None:
    with client() as c:
        m = c.get("/metrics").json()
        assert "category_accuracy" in m and "category_report" not in m


def test_batch_sorted_by_urgency() -> None:
    csv_text = (
        "subject,body\n"
        "idea,Please add dark mode. No rush just a small suggestion\n"
        "down,Production is down this is urgent need help immediately app crashes\n"
    )
    with client() as c:
        r = c.post("/predict/batch", files={"file": ("t.csv", csv_text, "text/csv")})
        assert r.status_code == 200
        rows = r.json()["results"]
        assert r.json()["count"] == 2
        assert rows[0]["subject"] == "down"


def test_batch_errors() -> None:
    with client() as c:
        bad = c.post("/predict/batch", files={"file": ("t.csv", "a,b\n1,2\n", "text/csv")})
        assert bad.status_code == 422
        empty = c.post("/predict/batch", files={"file": ("t.csv", "body\n", "text/csv")})
        assert empty.status_code == 422
        big = "body\n" + "x\n" * 501
        assert c.post("/predict/batch", files={"file": ("t.csv", big, "text/csv")}).status_code == 413
