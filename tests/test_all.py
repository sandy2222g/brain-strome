import itertools

import pytest
from fastapi.testclient import TestClient

from changemaker.api import app
from changemaker.core import ChangeError, build, fewest_coins, greedy, load

RAW = load()
TILL = build(RAW["till"], 0)
c = TestClient(app)


def count(plan):
    return None if plan is None else sum(plan.values())


def brute(till, amount):
    best = None
    for combo in itertools.product(*[range(n + 1) for n in till.values()]):
        if sum(k * q for k, q in zip(till, combo, strict=True)) == amount:
            n = sum(combo)
            best = n if best is None else min(best, n)
    return best


def test_matches_brute_force():
    small = {1: 4, 10: 2, 25: 1}
    for a in range(0, 50):
        assert count(fewest_coins(small, a)) == brute(small, a)


def test_greedy_loses_at_30():
    assert count(greedy(TILL, 30)) == 6 and count(fewest_coins(TILL, 30)) == 3


def test_change_sums_to_amount_and_respects_stock():
    for a in RAW["amounts"]:
        plan = fewest_coins(TILL, a)
        assert plan is not None
        assert sum(k * n for k, n in plan.items()) == a
        assert all(n <= TILL[k] for k, n in plan.items())


def test_never_worse_than_greedy():
    for a in range(0, 90):
        f, g = fewest_coins(TILL, a), greedy(TILL, a)
        if g is not None:
            assert f is not None and count(f) <= count(g)


def test_greedy_can_fail_when_change_exists():
    till = {1: 2, 10: 3, 25: 1}
    assert greedy(till, 30) is None and count(fewest_coins(till, 30)) == 3


def test_impossible():
    assert fewest_coins({10: 1}, 5) is None


def test_zero_amount():
    assert fewest_coins(TILL, 0) == {}


def test_validation():
    with pytest.raises(ChangeError):
        build({}, 5)
    with pytest.raises(ChangeError):
        build({"0": 1}, 5)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/change", json=c.get("/sample").json()).json()
    assert r["rows"][0]["fewest"]["coins"] == 3 and r["rows"][0]["greedy"]["coins"] == 6
    assert c.get("/").status_code == 200
    assert c.post("/change", json={"till": {}, "amounts": [5]}).status_code == 422
