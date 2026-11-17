import itertools

import pytest
from fastapi.testclient import TestClient

from cachelab.api import app
from cachelab.core import CacheError, compare, curve, fifo, lfu, lru, make_trace, optimal

c = TestClient(app)


def test_hand_worked_traces():
    t = [1, 2, 3, 1, 2, 4, 1, 2, 5]
    assert fifo(t, 3) == 2  # 1 and 2 are pushed out in arrival order, so later repeats miss
    assert lru(t, 3) == 4  # recent keys 1 and 2 stay; only 3 is evicted
    assert optimal(t, 3) == 4


def test_classic_belady_anomaly_for_fifo():
    t = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
    assert fifo(t, 3) == 3 and fifo(t, 4) == 2  # more memory, fewer hits
    assert lru(t, 4) >= lru(t, 3)  # LRU never suffers it


def test_optimal_is_an_upper_bound_on_random_traces():
    for seed in range(30):
        t = make_trace("zipf", 400, 30, seed)
        for size in (1, 3, 8):
            best = optimal(t, size)
            assert all(p(t, size) <= best for p in (fifo, lru, lfu))


def test_optimal_matches_brute_force_on_tiny_cases():
    def brute(t: list[int], size: int) -> int:
        best = 0
        def go(i: int, cache: frozenset[int], hits: int) -> None:
            nonlocal best
            if i == len(t):
                best = max(best, hits)
                return
            if t[i] in cache:
                go(i + 1, cache, hits + 1)
            elif len(cache) < size:
                go(i + 1, cache | {t[i]}, hits)
            else:
                for v in cache:
                    go(i + 1, (cache - {v}) | {t[i]}, hits)
        go(0, frozenset(), 0)
        return best

    for t in itertools.islice(itertools.product(range(4), repeat=7), 0, 2000, 37):
        assert optimal(list(t), 2) == brute(list(t), 2)


def test_scan_traffic_hurts_lru_but_not_lfu():
    r = {x["policy"]: x["hit_rate"] for x in compare("scan", 20)}
    assert r["lfu"] > r["lru"] + 0.05


def test_zipf_helps_lfu_and_uniform_is_flat():
    z = {x["policy"]: x["hit_rate"] for x in compare("zipf", 20)}
    u = {x["policy"]: x["hit_rate"] for x in compare("uniform", 20)}
    assert z["lfu"] >= z["fifo"] and z["optimal"] > 0.5
    assert max(u["fifo"], u["lru"], u["lfu"]) - min(u["fifo"], u["lru"], u["lfu"]) < 0.02  # no policy can guess
    assert u["optimal"] > 3 * u["lru"]  # only knowing the future helps


def test_bigger_cache_never_hurts_lru_or_optimal():
    cu = curve("zipf", [2, 10, 40, 160])
    for p in ("lru", "optimal"):
        assert cu[p] == sorted(cu[p])


def test_validation():
    with pytest.raises(CacheError):
        make_trace("weird")
    with pytest.raises(CacheError):
        compare("zipf", 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/curve", params={"kind": "scan"}).json()
    assert len(j["sizes"]) == 7 and set(j["curves"]) == {"fifo", "lru", "lfu", "optimal"}
    assert c.get("/curve", params={"kind": "x"}).status_code == 422 and c.get("/").status_code == 200
