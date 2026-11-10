from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import ROOT
from sniffer.api import app
from sniffer.categorize import CategoryModel
from sniffer.io import parse_csv
from sniffer.report import analyze


def test_category_model_generalises_to_unseen_names(cats: CategoryModel) -> None:
    assert cats.metrics["category_cv_accuracy"] >= 0.85
    assert cats.predict("COSMO MUSIC") == "music"
    assert cats.predict("ORBIT GYM") == "fitness"
    assert cats.predict("HILLSIDE ELECTRIC") == "utilities"


def test_analyze_sample_statement(cats: CategoryModel) -> None:
    res = analyze(parse_csv((ROOT / "data" / "transactions.csv").read_text()), cats)
    names = {s["merchant"] for s in res["subscriptions"]}
    assert {"STREAMBOX", "TUNENEST", "FITPASS GYM", "CLOUDVAULT", "NEWSDAILY", "MEALBOX"} <= names
    assert "GAMELOOP" not in names and any(e["merchant"] == "GAMELOOP" for e in res["ended"])
    assert {b["merchant"] for b in res["bills"]} >= {"HOMEKEY RENTALS", "POWERGRID ENERGY"}
    assert res["monthly_subscriptions"] > 100 and res["price_hike_annual_cost"] > 30
    assert abs(res["annual_subscriptions"] - 12 * res["monthly_subscriptions"]) < 12 * 1.0 + 5
    assert len(res["monthly_chart"]) == 14


def test_api() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Subscription Sniffer" in c.get("/").text
        m = c.get("/metrics").json()
        assert m["detect_recall"] >= 0.9 and "category_cv_accuracy" in m
        assert c.get("/sample").json()["subscriptions"]
        csv_bytes = (ROOT / "static" / "sample_statement.csv").read_bytes()
        r = c.post("/analyze/csv", files={"file": ("s.csv", csv_bytes, "text/csv")})
        assert r.status_code == 200 and r.json()["transactions"] > 400


def test_api_errors() -> None:
    with TestClient(app) as c:
        assert c.post("/analyze/csv", files={"file": ("s.csv", b"a,b\n1,2\n", "text/csv")}).status_code == 422
        big = b"x" * 2_000_001
        assert c.post("/analyze/csv", files={"file": ("s.csv", big, "text/csv")}).status_code == 413
        assert c.post("/analyze", json={"transactions": []}).status_code == 422
        bad = {"transactions": [{"date": "nope", "description": "X", "amount": 1}]}
        assert c.post("/analyze", json=bad).status_code == 422
        ok = {"transactions": [{"date": "2026-01-01", "description": "X", "amount": -1}]}
        assert c.post("/analyze", json=ok).status_code == 200


def test_overlap_only_flags_comparable_services(cats: CategoryModel) -> None:
    from datetime import date

    from conftest import monthly

    txns = (monthly("STREAMBOX", 9.99, date(2026, 1, 5), 4) + monthly("FILMFLIX PLUS", 7.99, date(2026, 1, 9), 4)
            + monthly("CLOUDVAULT", 2.99, date(2026, 1, 3), 4) + monthly("SHIELDVPN", 4.99, date(2026, 1, 4), 4))
    res = analyze(txns, cats)
    assert list(res["overlaps"]) == ["streaming"]
