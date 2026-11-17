import pytest
from fastapi.testclient import TestClient

from ratelab.api import app
from ratelab.core import FixedWindow, RateError, SlidingLog, TokenBucket, compare, make, simulate, traffic, worst_span

c = TestClient(app)


def test_each_limiter_allows_exactly_limit_in_an_instant_burst():
    for name in ("fixed_window", "sliding_log", "token_bucket"):
        assert sum(simulate(name, [0.5] * 20, 5, 10)) == 5


def test_fixed_window_resets_at_the_boundary():
    f = FixedWindow(2, 10)
    assert [f.allow(t) for t in (1, 2, 3, 9.9, 10.0, 10.1, 10.2)] == [True, True, False, False, True, True, False]


def test_sliding_log_blocks_edge_burst_that_fixed_window_lets_through():
    times = [9.9] * 5 + [10.1] * 5
    assert sum(simulate("fixed_window", times, 5, 10)) == 10  # twice the limit within 0.2 s
    assert sum(simulate("sliding_log", times, 5, 10)) == 5


def test_sliding_log_is_exact_oracle():
    lim = SlidingLog(3, 5)
    assert [lim.allow(t) for t in (0, 1, 2, 3, 5.0, 5.5, 6.0)] == [True, True, True, False, True, False, True]


def test_token_bucket_allows_burst_then_average_rate():
    b = TokenBucket(10, 10)  # 1 token/s, capacity 10
    assert sum(b.allow(0.0) for _ in range(15)) == 10
    assert not b.allow(0.5) and b.allow(1.0)
    assert sum(b.allow(100.0) for _ in range(30)) == 10  # refill capped at capacity


def test_edge_traffic_breaks_only_the_fixed_window():
    rows = {r["algorithm"]: r for r in compare("edge", 10, 10.0)}
    assert rows["fixed_window"]["worst_span"] > 10
    assert rows["sliding_log"]["worst_span"] <= 10
    assert rows["token_bucket"]["worst_span"] <= 20  # bucket can burst a full capacity plus refill


def test_traffic_is_deterministic_and_sorted():
    for k in ("steady", "bursty", "edge"):
        t = traffic(k, 60, 3)
        assert t == traffic(k, 60, 3) and t == sorted(t) and len(t) > 100 // 2


def test_worst_span_and_validation():
    assert worst_span([0, 1, 2, 20], [True] * 4, 5) == 3
    with pytest.raises(RateError):
        make("nope", 5, 1)
    with pytest.raises(RateError):
        make("token_bucket", 0, 1)
    with pytest.raises(RateError):
        traffic("weird")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/compare", params={"kind": "edge"}).json()
    assert len(j["rows"]) == 3 and len(j["times"]) == len(j["timeline"]["fixed_window"])
    assert c.get("/compare", params={"kind": "x"}).status_code == 422
    assert c.get("/compare", params={"limit": 0}).status_code == 422 and c.get("/").status_code == 200
