import itertools
import random

import pytest
from fastapi.testclient import TestClient

from bagbalance.api import app
from bagbalance.core import BagError, alternate, balance, load, over_limit

D = load()
ITEMS = D["items"]
c = TestClient(app)


def brute(items):
    total = sum(i["g"] for i in items)
    best = total
    for r in range(len(items) + 1):
        for combo in itertools.combinations(items, r):
            best = min(best, abs(total - 2 * sum(i["g"] for i in combo)))
    return best


def test_sample_difference_is_minimal():
    assert balance(ITEMS)["difference"] == brute(ITEMS) == 100


def test_alternating_is_much_worse():
    assert alternate(ITEMS)["difference"] == 6900


def test_every_item_in_exactly_one_bag():
    b = balance(ITEMS)
    names = [i["name"] for i in b["bag_a"] + b["bag_b"]]
    assert sorted(names) == sorted(i["name"] for i in ITEMS)


def test_weights_add_up():
    b = balance(ITEMS)
    assert b["weight_a"] + b["weight_b"] == sum(i["g"] for i in ITEMS)
    assert b["weight_a"] <= b["weight_b"]


def test_random_small_cases_near_optimal():
    rng = random.Random(7)
    for _ in range(40):
        items = [{"name": f"i{k}", "g": rng.randint(1, 60) * 10} for k in range(rng.randint(2, 9))]
        assert balance(items)["difference"] == brute(items)


def test_over_limit():
    assert over_limit(alternate(ITEMS), 11000) == ["weight_a"]
    assert over_limit(balance(ITEMS), 11000) == []


def test_validation():
    with pytest.raises(BagError):
        balance([{"name": "a", "g": 5}])
    with pytest.raises(BagError):
        balance([{"name": "a", "g": 0}, {"name": "b", "g": 5}])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/balance", json={"items": ITEMS, "bag_limit_g": 11000}).json()
    assert r["best"]["difference"] == 100 and r["alternating_over_limit"] == ["weight_a"]
    assert c.get("/").status_code == 200
    assert c.post("/balance", json={"items": [{"name": "a", "g": 1}]}).status_code == 422
