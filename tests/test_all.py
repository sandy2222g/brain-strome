import itertools
import random

import pytest
from fastapi.testclient import TestClient

from storageclean.api import app
from storageclean.core import CleanError, biggest_first, compare, load, optimal

D = load()
ITEMS, T = D["items"], D["target_mb"]
c = TestClient(app)


def mk(spec: list[tuple[int, int]]) -> list[dict[str, object]]:
    return [{"name": f"f{i}", "mb": mb, "keep": k} for i, (mb, k) in enumerate(spec)]


def brute(spec: list[tuple[int, int]], target: int) -> int:
    best = 10**9
    for r in range(len(spec) + 1):
        for combo in itertools.combinations(spec, r):
            if sum(m for m, _ in combo) >= target:
                best = min(best, sum(k for _, k in combo))
    return best


def test_small_by_hand():
    r = optimal(mk([(10, 5), (6, 1), (5, 1)]), 10)
    assert r["value_lost"] == 2 and {d["name"] for d in r["delete"]} == {"f1", "f2"}


def test_matches_brute_force():
    rng = random.Random(4)
    for _ in range(60):
        spec = [(rng.randint(1, 12), rng.randint(0, 9)) for _ in range(rng.randint(1, 9))]
        target = rng.randint(1, max(1, sum(m for m, _ in spec)))
        r = optimal(mk(spec), target)
        assert r["value_lost"] == brute(spec, target) and r["freed_mb"] >= target


def test_sample():
    r = compare(ITEMS, T)
    assert r["optimal"]["value_lost"] == 4 and r["optimal"]["freed_mb"] == 6100
    assert r["biggest_first"]["value_lost"] == 14 and r["value_saved"] == 10
    names = {d["name"] for d in r["optimal"]["delete"]}
    assert "Wedding photos" not in names and "Tax scans" not in names


def test_baseline_frees_enough_but_loses_more():
    b = biggest_first(ITEMS, T)
    assert b["freed_mb"] >= T and b["value_lost"] >= optimal(ITEMS, T)["value_lost"]


def test_exact_target_and_zero_value_items():
    r = optimal(mk([(5, 0), (5, 0)]), 10)
    assert r["freed_mb"] == 10 and r["value_lost"] == 0


def test_validation():
    for args in ([mk([(5, 1)]), 0], [mk([(5, 1)]), 10], [mk([(0, 1)]), 1], [mk([(5, -1)]), 1]):
        with pytest.raises(CleanError):
            optimal(*args)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/pick", json={"target_mb": T, "items": ITEMS}).json()
    assert r["value_saved"] == 10
    assert c.get("/").status_code == 200
    assert c.post("/pick", json={"target_mb": 10**6, "items": ITEMS}).status_code == 422
