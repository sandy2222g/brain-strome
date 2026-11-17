import pytest
from fastapi.testclient import TestClient

from liftsim.api import app
from liftsim.core import LiftError, Person, compare, load, pct, simulate

c = TestClient(app)


def test_single_trip_by_hand():
    # boards at t=0, doors 5 s, 3 floors x 2 s = 6 s travel (ride 11 s incl. doors), doors 5 s again
    r = simulate([Person(0, 0, 3)], "fcfs")
    assert r["mean_wait"] == 0 and r["mean_ride"] == 11 and r["finish_s"] == 16


def test_lift_must_travel_to_pickup():
    r = simulate([Person(0, 2, 0)], "nearest")
    assert r["mean_wait"] == 4  # two floors at 2 s each


def test_capacity_forces_second_trip():
    r = simulate([Person(0, 0, 1), Person(0, 0, 1)], "scan", capacity=1)
    # first: board 0, doors to 5, ride to 7, unload, doors to 12, return to 0 at 14, board second
    assert sorted([r["max_wait"], r["mean_wait"]]) == [7.0, 14]


def test_all_policies_finish_everyone():
    for pol in ("fcfs", "nearest", "scan"):
        r = simulate(load(), pol)
        assert r["finish_s"] > 0 and r["max_wait"] >= r["p90_wait"] >= r["mean_wait"] > 0


def test_nearest_and_scan_beat_fcfs_but_nearest_rides_longer():
    r = compare()
    assert r["fcfs"]["mean_wait"] == 201.8 and r["nearest"]["mean_wait"] == 160.2
    assert r["scan"]["mean_wait"] == 163.1
    assert r["nearest"]["mean_wait"] < r["fcfs"]["mean_wait"] and r["scan"]["mean_wait"] < r["fcfs"]["mean_wait"]
    assert r["nearest"]["mean_ride"] > r["scan"]["mean_ride"]


def test_small_capacity_does_not_livelock():
    # regression: a full lift ping-ponged between two waiting floors forever
    assert simulate(load(), "nearest", capacity=2)["finish_s"] == 2346


def test_percentile_helper():
    assert pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9) == 9


def test_validation():
    with pytest.raises(LiftError):
        simulate([Person(0, 0, 0)], "fcfs")
    with pytest.raises(LiftError):
        simulate([Person(0, 0, 99)], "fcfs")
    with pytest.raises(LiftError):
        simulate([Person(0, 0, 1)], "magic")
    with pytest.raises(LiftError):
        simulate([], "fcfs")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/sample").json()["trips"]) == 120
    r = c.post("/compare", json={}).json()["results"]
    assert r["scan"]["mean_wait"] == 163.1
    r2 = c.post("/compare", json={"trips": [{"time_s": 0, "origin": 0, "dest": 3}]}).json()["results"]
    assert r2["fcfs"]["mean_ride"] == 11
    assert c.post("/compare", json={"trips": [{"time_s": 0, "origin": 1, "dest": 1}]}).status_code == 422
    assert c.get("/").status_code == 200
