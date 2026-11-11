import itertools

import pytest
from fastapi.testclient import TestClient

from giftbudget.api import app
from giftbudget.core import GiftError, best_plan, build, equal_share_plan, load

RAW = load()
PEOPLE = build(RAW["people"], RAW["budget"])
c = TestClient(app)


def brute(people, budget):
    best = 0
    for combo in itertools.product(*[[None, *gs] for gs in people.values()]):
        cost = sum(g.price for g in combo if g)
        if cost <= budget:
            best = max(best, sum(g.joy for g in combo if g))
    return best


def test_matches_brute_force_on_sample():
    assert best_plan(PEOPLE, RAW["budget"])[0] == brute(PEOPLE, RAW["budget"])


def test_matches_brute_force_on_other_budgets():
    for b in (10, 35, 60, 90, 200):
        assert best_plan(PEOPLE, b)[0] == brute(PEOPLE, b)


def test_within_budget_and_consistent():
    joy, spent, chosen = best_plan(PEOPLE, 120)
    assert spent <= 120 and joy == sum(g.joy for g in chosen.values() if g)
    assert spent == sum(g.price for g in chosen.values() if g)


def test_optimal_beats_or_ties_equal_share():
    for b in (30, 60, 120, 180):
        assert best_plan(PEOPLE, b)[0] >= equal_share_plan(PEOPLE, b)[0]


def test_sample_gap():
    assert best_plan(PEOPLE, 120)[0] > equal_share_plan(PEOPLE, 120)[0]


def test_tiny_budget_buys_nothing():
    assert best_plan(PEOPLE, 5) == (0, 0, dict.fromkeys(PEOPLE))


def test_one_gift_each():
    assert set(best_plan(PEOPLE, 120)[2]) == set(PEOPLE)


def test_validation():
    with pytest.raises(GiftError):
        build({}, 10)
    with pytest.raises(GiftError):
        build({"a": [{"name": "x", "price": 0, "joy": 5}]}, 10)
    with pytest.raises(GiftError):
        build({"a": [{"name": "x", "price": 5, "joy": 11}]}, 10)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert r["optimal"]["joy"] > r["equal_share"]["joy"] and r["optimal"]["spent"] <= 120
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/plan", json={"budget": 0, "people": {}}).status_code == 422
