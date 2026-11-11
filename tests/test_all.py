import itertools
import random

import pytest
from fastapi.testclient import TestClient

from aislewalk.api import app
from aislewalk.core import (
    RouteError,
    best_route,
    check_items,
    dist,
    exact_order,
    heuristic_order,
    list_order_route,
    load,
    route_length,
    steps,
)

S = load()
NAMES = list(S.items)
c = TestClient(app)


def test_distance_same_aisle_is_depth_difference():
    assert dist(S, (2, 1), (2, 7)) == 6


def test_distance_uses_nearer_corridor_and_is_symmetric():
    assert dist(S, (0, 1), (3, 1)) == 1 + 9 + 1  # via front corridor
    assert dist(S, (0, 9), (3, 9)) == 1 + 9 + 1  # via back corridor
    assert dist(S, (1, 2), (5, 8)) == dist(S, (5, 8), (1, 2))


def test_triangle_inequality_on_random_points():
    rng = random.Random(0)
    pts = [(rng.randrange(8), rng.randrange(11)) for _ in range(30)]
    for a, b, k in itertools.product(pts[:8], pts[8:16], pts[16:24]):
        assert dist(S, a, k) <= dist(S, a, b) + dist(S, b, k)


def test_exact_matches_brute_force():
    rng = random.Random(4)
    for _ in range(12):
        items = rng.sample(NAMES, 6)
        brute = min(route_length(S, list(p)) for p in itertools.permutations(items))
        assert route_length(S, exact_order(S, items)) == brute


def test_exact_visits_each_item_once():
    items = random.Random(2).sample(NAMES, 9)
    assert sorted(exact_order(S, items)) == sorted(items)


def test_heuristic_close_to_exact_and_valid():
    rng = random.Random(5)
    for _ in range(8):
        items = rng.sample(NAMES, 10)
        h, e = route_length(S, heuristic_order(S, items)), route_length(S, exact_order(S, items))
        assert sorted(heuristic_order(S, items)) == sorted(items) and e <= h <= e * 1.15


def test_large_lists_use_heuristic_and_stay_valid():
    big = NAMES[:18]
    assert sorted(best_route(S, big)) == sorted(big)


def test_best_never_longer_than_list_order():
    rng = random.Random(6)
    for _ in range(20):
        items = rng.sample(NAMES, 8)
        assert route_length(S, best_route(S, items)) <= route_length(S, list_order_route(S, items))


def test_sample_list_saves_most_of_the_walk():
    items = ["milk", "apples", "pasta", "water", "bread", "tuna", "crisps", "dish soap", "eggs", "rice"]
    assert route_length(S, best_route(S, items)) < 0.5 * route_length(S, items)


def test_validation_and_dedup():
    with pytest.raises(RouteError):
        check_items(S, [])
    with pytest.raises(RouteError):
        check_items(S, ["unicorn"])
    assert check_items(S, ["milk", "milk", "eggs"]) == ["milk", "eggs"]


def test_steps_add_up_to_route_length():
    order = best_route(S, ["milk", "bread", "tuna"])
    st = steps(S, order)
    assert st[-1]["total"] == route_length(S, order) and st[-1]["item"] == "Checkout"


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert "milk" in c.get("/store").json()["items"]
    r = c.post("/route", json={"items": ["milk", "apples", "bread"]}).json()
    assert r["length"] <= r["list_order_length"] and len(r["steps"]) == 4
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/route", json={"items": []}).status_code == 422
    assert c.post("/route", json={"items": ["unicorn"]}).status_code == 422
