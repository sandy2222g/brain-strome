from __future__ import annotations

import pytest

from waitsim.erlang import mean_wait_min
from waitsim.recommend import recommend
from waitsim.sim import Config, percentile, run_once, simulate

FLAT = {"open_hour": 0, "close_hour": 24}


def test_simulation_matches_erlang_c_mean_wait() -> None:
    cfg = Config(arrivals_per_hour=20, mean_service_min=12, servers=5, **FLAT)
    s = simulate(cfg, replications=40, seed=3)
    analytic = mean_wait_min(5, 20, 12)
    assert abs(s.mean_wait_min - analytic) < max(1.5, 3 * s.mean_wait_ci95)


def test_utilisation_is_close_to_offered_load() -> None:
    s = simulate(Config(arrivals_per_hour=20, mean_service_min=12, servers=5, **FLAT), replications=20, seed=2)
    assert s.utilization == pytest.approx(20 * 12 / 60 / 5, abs=0.05)


def test_deterministic_for_a_seed() -> None:
    cfg = Config()
    assert simulate(cfg, 5, seed=4) == simulate(cfg, 5, seed=4)
    assert simulate(cfg, 5, seed=4) != simulate(cfg, 5, seed=5)


def test_more_staff_means_shorter_waits() -> None:
    waits = [simulate(Config(arrivals_per_hour=14, servers=c), 20, seed=1).mean_wait_min for c in (3, 4, 5, 6)]
    assert waits == sorted(waits, reverse=True) and waits[0] > 3 * waits[-1]


def test_urgent_patients_wait_less() -> None:
    s = simulate(Config(arrivals_per_hour=14, servers=3, urgent_share=0.3), 30, seed=1)
    assert s.mean_urgent_wait_min < s.mean_routine_wait_min


def test_walkouts_cut_the_queue_but_lose_patients() -> None:
    base = Config(arrivals_per_hour=18, servers=3)
    patient = simulate(base, 20, seed=1)
    impatient = simulate(Config(**{**base.__dict__, "mean_patience_min": 20}), 20, seed=1)
    assert impatient.abandon_rate > 0 and patient.abandon_rate == 0
    assert impatient.mean_wait_min < patient.mean_wait_min


def test_overloaded_system_grows_long_waits_and_overtime() -> None:
    s = simulate(Config(arrivals_per_hour=30, mean_service_min=12, servers=3), 10, seed=1)
    assert s.p95_wait_min > 60 and s.overtime_min > 30


def test_hourly_profile_shapes_arrivals() -> None:
    prof = tuple([0.0] * 8 + [3.0] + [0.0] * 15)
    r = run_once(Config(arrivals_per_hour=10, hourly_profile=prof, open_hour=0, close_hour=24), 1)
    assert r.arrived > 15  # about 30 expected, all in hour 8


def test_service_variability_matters() -> None:
    regular = simulate(Config(arrivals_per_hour=18, servers=3, service_cv=0.3), 30, seed=1).mean_wait_min
    erratic = simulate(Config(arrivals_per_hour=18, servers=3, service_cv=2.0), 30, seed=1).mean_wait_min
    assert erratic > regular


def test_percentile() -> None:
    assert percentile([], 0.5) == 0.0
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([5], 0.95) == 5


@pytest.mark.parametrize(
    "bad",
    [
        dict(arrivals_per_hour=0),
        dict(servers=0),
        dict(open_hour=10, close_hour=9),
        dict(urgent_share=2),
        dict(hourly_profile=(1.0,)),
        dict(service_cv=0),
    ],
)
def test_config_validation(bad: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(ValueError):
        Config(**bad).validate()


def test_replication_bounds() -> None:
    with pytest.raises(ValueError):
        simulate(Config(), replications=0)


def test_recommend_finds_smallest_team_that_meets_the_promise() -> None:
    cfg = Config(arrivals_per_hour=16, mean_service_min=12, servers=1)
    rec = recommend(cfg, target_min=20, level=0.9, replications=20, seed=1)
    by = {o["servers"]: o for o in rec["options"]}
    c = rec["recommended_servers"]
    assert by[c]["meets_target"] and (c - 1 not in by or not by[c - 1]["meets_target"])
    assert rec["analytic_start"] >= 4


def test_recommend_validation() -> None:
    with pytest.raises(ValueError):
        recommend(Config(), level=1.5)
    with pytest.raises(ValueError):
        recommend(Config(), target_min=0)


def test_hourly_wait_profile_peaks_when_arrivals_peak() -> None:
    prof = tuple([0.0] * 8 + [0.3, 2.5, 2.5, 0.3] + [0.0] * 12)
    s = simulate(Config(arrivals_per_hour=12, servers=3, hourly_profile=prof), 30, seed=1)
    assert len(s.hourly_wait_min) == 24 and s.hourly_wait_min[10] > s.hourly_wait_min[8]
