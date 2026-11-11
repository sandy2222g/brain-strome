import itertools
import random

import pytest
from fastapi.testclient import TestClient

from tripstops.api import app
from tripstops.core import Stop, TripError, load, naive_plan, plan, summary, validate

LEN, STOPS = load()
c = TestClient(app)


def brute(length, stops, rng_km, leg):
    best = None
    for r in range(len(stops) + 1):
        for combo in itertools.combinations(sorted(stops, key=lambda s: s.km), r):
            if validate(length, list(combo), rng_km, leg):
                cost = (len(combo), sum(s.price for s in combo if s.fuels))
                best = cost if best is None or cost < best else best
    return best


def test_sample_plan_is_valid():
    assert validate(LEN, plan(LEN, STOPS, 220, 130), 220, 130)


def test_matches_brute_force_on_random_routes():
    rng = random.Random(11)
    for _ in range(60):
        n = rng.randint(3, 8)
        kms = sorted(rng.sample(range(10, 290), n))
        kinds = ["fuel", "break", "both"]
        stops = [Stop(f"s{i}", float(k), rng.choice(kinds), round(rng.uniform(1.5, 2.0), 2)) for i, k in enumerate(kms)]
        expect = brute(300.0, stops, 150.0, 110.0)
        if expect is None:
            with pytest.raises(TripError):
                plan(300.0, stops, 150.0, 110.0)
        else:
            got = plan(300.0, stops, 150.0, 110.0)
            assert (len(got), sum(s.price for s in got if s.fuels)) == pytest.approx(expect)


def test_never_worse_than_naive():
    for rng_km, leg in ((220, 130), (260, 100), (200, 150)):
        try:
            naive = naive_plan(LEN, STOPS, rng_km, leg)
        except TripError:
            continue
        assert len(plan(LEN, STOPS, rng_km, leg)) <= len(naive)


def test_looser_limits_never_need_more_stops():
    assert len(plan(LEN, STOPS, 300, 200)) <= len(plan(LEN, STOPS, 220, 100))


def test_impossible_when_gap_too_big():
    with pytest.raises(TripError):
        plan(LEN, STOPS, 220, 20)


def test_bad_inputs():
    with pytest.raises(TripError):
        plan(LEN, STOPS, 0, 100)
    with pytest.raises(TripError):
        plan(100.0, [Stop("x", 150.0, "fuel", 1.0)], 100, 100)


def test_validate_detects_bad_plans():
    assert not validate(LEN, [], 220, 130)


def test_summary_counts():
    s = summary([Stop("a", 1, "fuel", 2.0), Stop("b", 2, "break")])
    assert s == {"stops": 2, "fuel_stops": 1, "avg_fuel_price": 2.0}


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/route").json()["stops"]) == len(STOPS)
    r = c.post("/plan", json={"range_km": 220, "max_leg_km": 130}).json()
    assert r["summary"]["stops"] <= r["naive_summary"]["stops"]
    assert c.get("/").status_code == 200


def test_api_impossible_422():
    assert c.post("/plan", json={"range_km": 30, "max_leg_km": 30}).status_code == 422
    assert c.post("/plan", json={"range_km": 5, "max_leg_km": 30}).status_code == 422
