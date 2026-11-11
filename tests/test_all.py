import random

import pytest
from fastapi.testclient import TestClient

from tippool.api import app
from tippool.core import TipError, Worker, build, largest_remainder, load, naive_rounding

S = load()
W = build(S["workers"], S["pool_cents"])
c = TestClient(app)


def test_even_split_of_100_among_three():
    assert sorted(largest_remainder(W, 10000).values()) == [3333, 3333, 3334]


def test_naive_rounding_loses_a_cent():
    assert sum(naive_rounding(W, 10000).values()) == 9999


def test_total_always_exact():
    rng = random.Random(4)
    for _ in range(300):
        ws = [Worker(f"w{i}", rng.randint(1, 40) / 2) for i in range(rng.randint(1, 9))]
        pool = rng.randint(0, 50_000)
        assert sum(largest_remainder(ws, pool).values()) == pool


def test_within_one_cent_of_exact_share():
    ws = [Worker("a", 7.5), Worker("b", 12), Worker("c", 3.25)]
    got, total = largest_remainder(ws, 12345), sum(w.hours for w in ws)
    for w in ws:
        assert abs(got[w.name] - 12345 * w.hours / total) < 1


def test_more_hours_never_gets_less():
    ws = [Worker("a", 5), Worker("b", 8), Worker("c", 8.5)]
    got = largest_remainder(ws, 9999)
    assert got["a"] <= got["b"] <= got["c"]


def test_single_worker_gets_everything():
    assert largest_remainder([Worker("a", 3)], 777) == {"a": 777}


def test_zero_pool():
    assert set(largest_remainder(W, 0).values()) == {0}


def test_validation():
    with pytest.raises(TipError):
        build([], 100)
    with pytest.raises(TipError):
        build([{"name": "a", "hours": 0}], 100)
    with pytest.raises(TipError):
        build([{"name": "a", "hours": 1}, {"name": "a", "hours": 2}], 100)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/split", json=c.get("/sample").json()).json()
    assert r["fair_total"] == 10000 and r["naive_total"] == 9999
    assert c.get("/").status_code == 200
    assert c.post("/split", json={"pool_cents": 5, "workers": []}).status_code == 422
