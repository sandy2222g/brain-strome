from __future__ import annotations

import math

import pytest

from waitsim.erlang import mean_wait_min, min_servers, offered_load, prob_wait, service_level


def test_offered_load() -> None:
    assert offered_load(30, 12) == 6.0


def test_prob_wait_known_values() -> None:
    assert prob_wait(1, 0.5) == pytest.approx(0.5)  # M/M/1: P(wait) = rho
    assert prob_wait(2, 1.0) == pytest.approx(1 / 3, abs=1e-9)  # textbook Erlang C example
    assert prob_wait(3, 3.0) == 1.0 and prob_wait(3, 5.0) == 1.0


def test_mean_wait_mm1_formula() -> None:
    # M/M/1: Wq = rho / (mu - lambda); lambda=6/h, service 6 min -> rho .6, Wq = .6 * 6 / (1 - .6) = 9 min
    assert mean_wait_min(1, 6, 6) == pytest.approx(9.0)
    assert mean_wait_min(1, 10, 6) == math.inf


def test_service_level_bounds_and_monotone() -> None:
    a = service_level(3, 20, 6, 5)
    b = service_level(3, 20, 6, 15)
    assert 0 < a < b < 1
    assert service_level(1, 20, 6, 5) == 0.0
    assert service_level(5, 20, 6, 5) > a


def test_min_servers_meets_level_and_is_minimal() -> None:
    c = min_servers(30, 10, 10, 0.9)
    assert service_level(c, 30, 10, 10) >= 0.9
    assert c == 5 or service_level(c - 1, 30, 10, 10) < 0.9


@pytest.mark.parametrize("args", [(0, 1.0), (2, -1.0)])
def test_validation(args: tuple[int, float]) -> None:
    with pytest.raises(ValueError):
        prob_wait(*args)


def test_demand_too_high() -> None:
    with pytest.raises(ValueError, match="too high"):
        min_servers(100000, 60, 1, 0.99)
