import itertools
import random

import pytest
from fastapi.testclient import TestClient

from swimlane.api import app
from swimlane.core import LaneError, assign, compare, load, signup_order

D = load()
SW, L, CAP = D["swimmers"], D["lanes"], D["capacity"]
c = TestClient(app)


def mk(times: list[float]) -> list[dict[str, object]]:
    return [{"name": f"s{i}", "time100": t} for i, t in enumerate(times)]


def brute(times: list[float], k: int, cap: int) -> float:
    t = sorted(times)
    n, best = len(t), float("inf")
    for cuts in itertools.combinations(range(1, n), k - 1):
        b = [0, *cuts, n]
        if any(b[i + 1] - b[i] > cap for i in range(k)):
            continue
        best = min(best, sum(t[b[i + 1] - 1] - t[b[i]] for i in range(k)))
    return best


def test_obvious_split():
    r = assign(mk([60, 61, 100, 101]), 2, 3)
    assert [x["swimmers"] for x in r["lanes"]] == [["s0", "s1"], ["s2", "s3"]]
    assert r["total_spread"] == 2.0


def test_matches_brute_force():
    rng = random.Random(3)
    for _ in range(40):
        n = rng.randint(2, 9)
        k = rng.randint(2, min(4, n))
        cap = rng.randint(-(-n // k), n)
        times = [round(rng.uniform(60, 140), 1) for _ in range(n)]
        assert assign(mk(times), k, cap)["total_spread"] == pytest.approx(brute(times, k, cap), abs=0.05)


def test_capacity_and_everyone_placed():
    r = assign(SW, L, CAP)
    names = [n for lane in r["lanes"] for n in lane["swimmers"]]
    assert sorted(names) == sorted(s["name"] for s in SW)
    assert all(len(lane["swimmers"]) <= CAP for lane in r["lanes"])


def test_lanes_are_ordered_fast_to_slow():
    lanes = assign(SW, L, CAP)["lanes"]
    assert all(a["slowest"] <= b["fastest"] for a, b in itertools.pairwise(lanes))


def test_sample_beats_signup_order():
    r = compare(SW, L, CAP)
    assert r["assigned"]["total_spread"] == 42.6 and r["spread_saved"] == 250.0
    assert signup_order(SW, L, CAP)["total_spread"] == 292.6


def test_fewer_swimmers_than_lanes():
    assert len(assign(mk([70, 80]), 6, 4)["lanes"]) == 2


def test_validation():
    for args in ([[], 2, 2], [mk([70, 80, 90]), 1, 2], [mk([0, 80]), 2, 2], [mk([70]), 0, 2]):
        with pytest.raises(LaneError):
            assign(*args)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/assign", json={"lanes": L, "capacity": CAP, "swimmers": SW}).json()
    assert r["spread_saved"] == 250.0
    assert c.get("/").status_code == 200
    assert c.post("/assign", json={"lanes": 1, "capacity": 1, "swimmers": SW}).status_code == 422
