import itertools
import random

import pytest
from fastapi.testclient import TestClient

from shelffill.api import app
from shelffill.core import ShelfError, compare, greedy, load, optimal

D = load()
BOOKS, W = D["books"], D["shelf_width"]
c = TestClient(app)


def mk(spec: list[tuple[float, float]]) -> list[dict[str, object]]:
    return [{"title": f"b{i}", "thickness": t, "height": h} for i, (t, h) in enumerate(spec)]


def brute(spec: list[tuple[float, float]], width: float) -> float:
    n, best = len(spec), float("inf")
    for r in range(n):
        for mid in itertools.combinations(range(1, n), r):
            cuts = [0, *mid, n]
            parts = [spec[a:b] for a, b in itertools.pairwise(cuts)]
            if any(sum(t for t, _ in p) > width for p in parts):
                continue
            best = min(best, sum(max(h for _, h in p) for p in parts))
    return best


def test_small_by_hand():
    # tall book last: greedy puts it with the short ones, optimal does the same here; width forces 2 shelves
    r = optimal(mk([(5, 10), (5, 10), (5, 30)]), 10)
    assert r["total_height"] == 40 and r["count"] == 2


def test_optimal_beats_greedy_case():
    spec = [(6, 10), (4, 30), (6, 30), (6, 30), (6, 10)]
    assert optimal(mk(spec), 10)["total_height"] == 80 and greedy(mk(spec), 10)["total_height"] == 100


def test_matches_brute_force():
    rng = random.Random(8)
    for _ in range(40):
        spec = [(rng.randint(1, 5), rng.randint(10, 40)) for _ in range(rng.randint(1, 9))]
        width = rng.randint(5, 14)
        assert optimal(mk(spec), width)["total_height"] == brute(spec, width)


def test_never_worse_than_greedy_and_order_kept():
    r = compare(BOOKS, W)
    assert r["optimal"]["total_height"] <= r["greedy"]["total_height"]
    order = [t for s in r["optimal"]["shelves"] for t in s["books"]]
    assert order == [b["title"] for b in BOOKS]
    assert all(s["used"] <= W for s in r["optimal"]["shelves"])


def test_sample_numbers():
    r = compare(BOOKS, W)
    assert (r["optimal"]["total_height"], r["greedy"]["total_height"], r["height_saved"]) == (110.0, 128.0, 18.0)


def test_validation():
    for args in ([[], 10], [mk([(5, 5)]), 0], [mk([(15, 5)]), 10], [mk([(0, 5)]), 10]):
        with pytest.raises(ShelfError):
            optimal(*args)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/fill", json={"shelf_width": W, "books": BOOKS}).json()
    assert r["height_saved"] == 18.0
    assert c.get("/").status_code == 200
    assert c.post("/fill", json={"shelf_width": 1, "books": BOOKS}).status_code == 422
