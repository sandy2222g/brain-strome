import pytest
from fastapi.testclient import TestClient

from billtime.api import app
from billtime.core import BillError, balances, load, shortfalls, suggest_moves

M = load()
c = TestClient(app)


def test_balance_by_hand():
    b = balances(M)
    assert b[0] == -550.0  # 150 - 700 rent
    assert b[4] == 315.0  # day 5: 150-700-35+900
    assert b[-1] == 645.0


def test_total_matches_money_in_minus_out():
    total_in = sum(i["amount"] for i in M["income"])
    total_out = sum(b["amount"] for b in M["bills"])
    assert balances(M)[-1] == pytest.approx(M["opening_balance"] + total_in - total_out)


def test_shortfall_days_found():
    days = [s["day"] for s in shortfalls(balances(M))]
    assert days[:4] == [1, 2, 3, 4] and 14 in days and 19 not in days


def test_suggested_moves_clear_shortfalls():
    fix = suggest_moves(M)
    assert fix["shortfalls"] == []
    assert fix["moves"] == {"Rent@1": 5, "Insurance@12": 19}


def test_moves_keep_the_month_total():
    fix = suggest_moves(M)
    assert fix["balances"][-1] == balances(M)[-1]


def test_nothing_to_fix_when_flush():
    rich = {**M, "opening_balance": 5000.0}
    assert suggest_moves(rich)["moves"] == {}


def test_unfixable_month_reports_remaining():
    poor = {**M, "income": [{"name": "Pay", "day": 5, "amount": 10.0}]}
    assert suggest_moves(poor)["shortfalls"]


def test_validation():
    with pytest.raises(BillError):
        balances({**M, "bills": [{"name": "x", "day": 40, "amount": 1}]})
    with pytest.raises(BillError):
        balances({**M, "bills": [{"name": "x", "day": 3, "amount": -1}]})
    with pytest.raises(BillError):
        balances(M, {"Rent@1": 99})


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/check", json=c.get("/sample").json()).json()
    assert r["shortfalls"] and r["fix"]["shortfalls"] == []
    assert c.get("/").status_code == 200
    bad = {"days": 5, "opening_balance": 0, "income": [], "bills": [{"name": "x", "day": 9, "amount": 1}]}
    assert c.post("/check", json=bad).status_code == 422
