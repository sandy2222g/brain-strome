import pytest
from fastapi.testclient import TestClient

from savegoal.api import app
from savegoal.core import (
    GoalError,
    balance_curve,
    load,
    months_to_goal,
    months_without_interest,
    required_monthly,
)

S = load()
c = TestClient(app)


def test_zero_rate_matches_simple_division():
    assert months_to_goal(1000, 100, 100, 0.0) == 9 == months_without_interest(1000, 100, 100)


def test_interest_never_slower():
    assert months_to_goal(5000, 500, 150, 0.04) <= months_without_interest(5000, 500, 150)


def test_sample_months():
    assert months_to_goal(S["goal"], S["start"], S["monthly"], S["annual_rate"]) == 29
    assert months_without_interest(S["goal"], S["start"], S["monthly"]) == 30


def test_closed_form_hits_goal():
    for rate in (0.0, 0.02, 0.06):
        dep = required_monthly(5000, 500, 24, rate)
        assert balance_curve(500, dep, rate, 24)[-1] == pytest.approx(5000, abs=0.01)


def test_required_monthly_by_hand_zero_rate():
    assert required_monthly(5000, 500, 24, 0.0) == pytest.approx(4500 / 24)


def test_already_there():
    assert months_to_goal(100, 200, 0, 0.03) == 0
    assert required_monthly(100, 200, 12, 0.03) == 0.0


def test_unreachable_returns_none():
    assert months_to_goal(1000, 0, 0, 0.05) is None


def test_curve_is_increasing():
    curve = balance_curve(500, 150, 0.04, 12)
    assert curve == sorted(curve) and len(curve) == 13


def test_validation():
    with pytest.raises(GoalError):
        months_to_goal(0, 0, 10, 0.01)
    with pytest.raises(GoalError):
        required_monthly(100, 0, 0, 0.01)
    with pytest.raises(GoalError):
        months_to_goal(100, 0, 10, 0.9)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert r["months_with_interest"] == 29 and r["months_without_interest"] == 30
    assert r["required_monthly"] < r["required_monthly_no_interest"]
    assert c.get("/").status_code == 200
    assert c.post("/plan", json={**S, "goal": 0}).status_code == 422
