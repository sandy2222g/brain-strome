import pytest
from fastapi.testclient import TestClient

from chasewin.api import app
from chasewin.core import ChaseError, analyse, check_probs, load, run_rate_baseline, simulate, win_probability

D = load()
P = D["presets"]["balanced"]
S = D["scenario"]
c = TestClient(app)


def test_certain_outcomes():
    assert win_probability(P, 100, 100, 3, 10) == 1.0  # already there
    assert win_probability(P, 100, 50, 10, 30) == 0.0  # all out
    assert win_probability(P, 100, 50, 3, 0) == 0.0  # no balls left


def test_one_ball_by_hand():
    # Nine down, one ball left. A wide scores 1 without using the ball: f(n) = P(runs >= n) + 0.08 * f(n-1).
    f1 = win_probability(P, 1, 0, 9, 1)  # need 1: any 1, 2, 3, 4, 6 or an extra wins
    assert f1 == pytest.approx(0.30 + 0.07 + 0.01 + 0.10 + 0.05 + 0.08)
    f4 = win_probability(P, 4, 0, 9, 1)
    f3 = win_probability(P, 3, 0, 9, 1)
    f2 = win_probability(P, 2, 0, 9, 1)
    assert f2 == pytest.approx(0.07 + 0.01 + 0.10 + 0.05 + 0.08 * f1)
    assert f3 == pytest.approx(0.01 + 0.10 + 0.05 + 0.08 * f2)
    assert f4 == pytest.approx(0.10 + 0.05 + 0.08 * f3)


def test_matches_monte_carlo():
    exact = win_probability(P, S["target"], S["runs"], S["wickets"], S["balls_left"])
    sim = simulate(P, S["target"], S["runs"], S["wickets"], S["balls_left"], 40000, seed=1)
    assert abs(exact - sim) < 0.012
    assert exact == pytest.approx(0.189, abs=0.001)


def test_monotonic():
    base = win_probability(P, 168, 92, 4, 48)
    assert win_probability(P, 168, 92, 6, 48) < base < win_probability(P, 168, 92, 2, 48)  # wickets in hand
    assert win_probability(P, 168, 92, 4, 36) < base < win_probability(P, 168, 92, 4, 60)  # balls left
    assert win_probability(P, 180, 92, 4, 48) < base < win_probability(P, 160, 92, 4, 48)  # target


def test_presets_change_the_odds():
    r = analyse("balanced", S["target"], S["runs"], S["wickets"], S["balls_left"])
    by = r["by_preset"]
    assert by["aggressive"] > by["balanced"] > by["defensive"]
    assert r["win_probability"] == by["balanced"]


def test_baseline_ignores_wickets():
    b = run_rate_baseline(168, 92, 48, 72)
    assert b == {"required_rate": 9.5, "current_rate": 7.67, "verdict": "behind"}
    assert run_rate_baseline(100, 50, 0, 60)["required_rate"] == float("inf")


def test_validation():
    with pytest.raises(ChaseError):
        check_probs({**P, "dot": 0.9})
    with pytest.raises(ChaseError):
        check_probs({"dot": 1.0})
    for args in ((0, 0, 0, 10), (100, 0, 11, 10), (100, 0, 0, 301), (600, 0, 0, 10)):
        with pytest.raises(ChaseError):
            win_probability(P, *args)
    with pytest.raises(ChaseError):
        analyse("reckless", 100, 0, 0, 60)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/estimate", json=S).json()
    assert r["win_probability"] == pytest.approx(0.189, abs=0.001) and r["baseline"]["verdict"] == "behind"
    assert c.post("/estimate", json={**S, "preset": "x"}).status_code == 422
    assert c.post("/estimate", json={**S, "wickets": 12}).status_code == 422
    assert c.get("/").status_code == 200
