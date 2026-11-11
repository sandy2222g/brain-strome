import json
from pathlib import Path

from fastapi.testclient import TestClient

from settler.api import app

c = TestClient(app)


def test_health_and_index():
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/").status_code == 200


def test_sample_settles():
    body = c.get("/sample").json()
    r = c.post("/settle", json=body).json()
    assert r["payment_count"] <= r["naive_count"]
    assert abs(sum(r["balances"].values())) < 0.01
    assert r["total_spent"] > 0


def test_payments_clear_balances():
    r = c.post("/settle", json=json.loads(Path("data/sample_flat.json").read_text())).json()
    bal = dict(r["balances"])
    for p in r["payments"]:
        bal[p["from"]] += p["amount"]
        bal[p["to"]] -= p["amount"]
    assert all(abs(v) < 0.01 for v in bal.values())


def test_validation_errors():
    assert c.post("/settle", json={"expenses": []}).status_code == 422
    bad = {"expenses": [{"payer": "a", "amount": -5, "split_among": ["a"]}]}
    assert c.post("/settle", json=bad).status_code == 422
    dup = {"expenses": [{"payer": "a", "amount": 5, "split_among": ["a", "a"]}]}
    assert c.post("/settle", json=dup).status_code == 422
