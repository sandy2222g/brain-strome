import itertools
import random

import pytest
from fastapi.testclient import TestClient

from debtplan.api import app
from debtplan.core import DebtError, cents, compare, load, simulate

D = load()
DEBTS, BUDGET = D["debts"], D["budget"]
c = TestClient(app)


def test_one_debt_by_hand():
    one = [{"name": "x", "balance": 1000.0, "apr": 12.0, "minimum": 100.0}]
    r = simulate(one, 100.0, "avalanche")
    # 1% a month on a 1000 balance paid 100 a month: 11 months
    assert r["months"] == 11 and r["balances"][0] == 1000.0 and r["balances"][-1] == 0.0


def test_interest_free_debt_costs_no_interest():
    z = [{"name": "z", "balance": 300.0, "apr": 0.0, "minimum": 50.0}]
    r = simulate(z, 50.0, "snowball")
    assert r["interest"] == 0.0 and r["months"] == 6


def test_money_adds_up():
    # total principal plus interest equals the money paid; with a constant budget until the last month
    r = simulate(DEBTS, BUDGET, "avalanche")
    principal = sum(cents(d["balance"]) for d in DEBTS) / 100
    assert r["balances"][0] == principal
    paid = principal + r["interest"]
    assert BUDGET * (r["months"] - 1) < paid <= BUDGET * r["months"]


def test_sample_results():
    r = compare(DEBTS, BUDGET)
    assert r["plans"]["avalanche"]["months"] == 27 and r["plans"]["avalanche"]["interest"] == pytest.approx(1940.87)
    assert r["interest_saved_vs_snowball"] == pytest.approx(77.65, abs=0.01)
    assert r["interest_saved_vs_minimum"] > 3000
    assert r["plans"]["snowball"]["paid_off_order"][0] == "Phone plan balance"


def test_avalanche_is_optimal_among_all_priorities():
    names = [d["name"] for d in DEBTS]
    best = min(simulate(DEBTS, BUDGET, list(p))["interest"] for p in itertools.permutations(names))
    assert simulate(DEBTS, BUDGET, "avalanche")["interest"] == pytest.approx(best)


def test_avalanche_never_worse_than_snowball_on_random_debts():
    rng = random.Random(5)
    for _ in range(25):
        debts = [
            {"name": f"d{i}", "balance": rng.randint(200, 5000), "apr": rng.randint(0, 30), "minimum": 25.0}
            for i in range(rng.randint(2, 4))
        ]
        budget = sum(d["minimum"] for d in debts) + rng.randint(20, 200)
        try:
            a, s = simulate(debts, budget, "avalanche"), simulate(debts, budget, "snowball")
        except DebtError:
            continue  # budget too small to ever clear these debts
        assert a["interest"] <= s["interest"] + 0.01


def test_validation():
    with pytest.raises(DebtError):
        simulate([], 100, "avalanche")
    with pytest.raises(DebtError):
        simulate(DEBTS, 50, "avalanche")  # budget below the minimums
    with pytest.raises(DebtError):
        simulate(DEBTS, BUDGET, "yolo")
    with pytest.raises(DebtError):
        simulate([{"name": "a", "balance": 1000, "apr": 50, "minimum": 1}], 1, "avalanche")  # never clears


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/compare", json={"budget": BUDGET, "debts": DEBTS}).json()
    assert r["plans"]["avalanche"]["months"] == 27
    assert c.get("/").status_code == 200
    assert c.post("/compare", json={"budget": 10, "debts": DEBTS}).status_code == 422
