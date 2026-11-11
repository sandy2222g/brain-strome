import pytest
from fastapi.testclient import TestClient

from leavetime.api import app
from leavetime.core import (
    LeaveError,
    Trip,
    bucket,
    fixed_buffer_rate,
    hhmm,
    leave_by,
    load,
    on_time_rate,
    predict_minutes,
    quantile,
    split,
    times_for,
)

TRIPS = load()
TRAIN, TEST = split(TRIPS)
c = TestClient(app)


def test_quantile_conservative_and_monotone():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert quantile(v, 0.9) == 9 and quantile(v, 0.5) == 5
    assert quantile(v, 0.2) <= quantile(v, 0.8)


def test_quantile_validation():
    with pytest.raises(LeaveError):
        quantile([], 0.5)
    with pytest.raises(LeaveError):
        quantile([1, 2], 1.5)


def test_bucket_and_hhmm():
    assert bucket(8.4) == 16 and hhmm(8.5) == "08:30" and hhmm(17.75) == "17:45"


def test_split_is_chronological_and_complete():
    assert len(TRAIN) + len(TEST) == len(TRIPS) and TRAIN + TEST == TRIPS


def test_widening_finds_enough_history():
    assert len(times_for(TRAIN, 9.5)) >= 15


def test_not_enough_data_raises():
    with pytest.raises(LeaveError):
        times_for([Trip(0, 8.0, 30.0)] * 3, 8.0)


def test_higher_confidence_means_more_minutes_and_earlier_departure():
    a = leave_by(TRAIN, 9.0, 0.7)
    b = leave_by(TRAIN, 9.0, 0.95)
    assert b["minutes_needed"] >= a["minutes_needed"] and b["leave_hour"] <= a["leave_hour"]


def test_leave_by_actually_arrives_in_time():
    r = leave_by(TRAIN, 9.0, 0.9)
    assert r["leave_hour"] + r["minutes_needed"] / 60 <= 9.0 + 1e-9


def test_calibration_tracks_target_within_tolerance():
    for q in (0.7, 0.8, 0.9):
        assert abs(on_time_rate(TRAIN, TEST, q) - q) < 0.1


def test_on_time_rate_increases_with_confidence():
    r = [on_time_rate(TRAIN, TEST, q) for q in (0.5, 0.8, 0.95)]
    assert r == sorted(r)


def test_fixed_buffer_baseline_is_a_rate():
    assert 0 <= fixed_buffer_rate(TRAIN, TEST) <= 1


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json={"arrive_hour": 9.0, "confidence": 0.9}).json()
    assert r["buffer_minutes"] >= 0 and r["leave_time"] < "09:00"
    cal = c.get("/calibration").json()
    assert len(cal["levels"]) == 5 and c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/plan", json={"arrive_hour": 3, "confidence": 0.9}).status_code == 422
    assert c.post("/plan", json={"arrive_hour": 9, "confidence": 0.2}).status_code == 422


def test_rush_hour_takes_longer_than_early_morning():
    assert predict_minutes(TRAIN, 8.3, 0.5) > predict_minutes(TRAIN, 7.5, 0.5)
