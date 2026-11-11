import itertools
import random

import pytest
from fastapi.testclient import TestClient

from heatplan.api import app
from heatplan.core import (
    Day,
    HeatError,
    House,
    load,
    optimise,
    simulate,
    snap,
    step_temp,
    target_at,
    thermostat,
    validate,
)

D = load()
c = TestClient(app)


def small_day(hours: int, seed: int) -> Day:
    rng = random.Random(seed)
    return Day(
        House(0.08, 2.0, 3.0, 17.0),
        [rng.uniform(0, 8) for _ in range(hours)],
        [rng.choice([0.1, 0.2, 0.4]) for _ in range(hours)],
        [(3.0, hours + 0.0, 19.0)],
    )


def test_physics_heater_warms_and_cold_outdoor_cools():
    h = House(0.06, 2.2, 3.0, 17.0)
    assert step_temp(h, 17, 3, True) > step_temp(h, 17, 3, False)
    assert step_temp(h, 17, 3, False) < 17 < step_temp(h, 17, 25, False)


def test_snap_rounds_to_a_tenth():
    assert snap(19.04) == 19.0 and snap(19.06) == 19.1


def test_target_at_wraps_over_days():
    assert target_at(D, 7) == 19 and target_at(D, 7 + 24) == 19 and target_at(D, 3) is None


def test_dp_matches_brute_force_within_snap_error():
    for seed in range(6):
        d = small_day(9, seed)
        best = simulate(d, optimise(d))["total"]
        brute = min(simulate(d, list(p))["total"] for p in itertools.product([False, True], repeat=9))
        assert best <= brute + 0.5  # state snapping to 0.1 C can cost a few cents at most


def test_optimised_beats_thermostat_on_sample():
    o = simulate(D, optimise(D))
    t = simulate(D, thermostat(D, 20.5))
    assert o["total"] < t["total"] and o["energy_cost"] <= t["energy_cost"]
    assert o["cold_degree_hours"] < t["cold_degree_hours"]


def test_optimised_shifts_heating_to_cheaper_hours():
    sched = optimise(D)
    on_prices = [p for p, on in zip(D.price, sched, strict=True) if on]
    assert sum(on_prices) / len(on_prices) < sum(D.price) / len(D.price)


def test_no_heating_costs_nothing_but_gets_cold():
    r = simulate(D, [False] * D.hours)
    assert r["energy_cost"] == 0 and r["cold_degree_hours"] > 10


def test_validation():
    with pytest.raises(HeatError):
        validate(Day(House(0.06, 2.0, 3.0, 17.0), [1.0], [0.1, 0.2], []))
    with pytest.raises(HeatError):
        validate(Day(House(0.0, 2.0, 3.0, 17.0), [1.0], [0.1], []))


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/day").json()["price"]) == 48
    body = {"start_temp": 17, "comfort_target": 20.5, "thermostat_setpoint": 20.5}
    r = c.post("/plan", json=body).json()
    assert r["optimised"]["total"] < r["thermostat"]["total"] and len(r["optimised"]["schedule"]) == 48
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/plan", json={"start_temp": 80}).status_code == 422
