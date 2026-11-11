from datetime import date

import pytest
from fastapi.testclient import TestClient

from jetlag.api import app
from jetlag.core import EAST_RATE, WEST_RATE, TripError, fmt, hour_shift, plan

D = date(2026, 11, 20)
c = TestClient(app)


def test_hour_shift_known_pairs():
    assert hour_shift("Europe/London", "Asia/Tokyo", D) == 9.0
    assert hour_shift("Asia/Kolkata", "Asia/Kolkata", D) == 0.0
    assert hour_shift("America/New_York", "Europe/London", D) == 5.0


def test_shorter_way_around_the_clock():
    s = hour_shift("Asia/Tokyo", "America/Los_Angeles", D)  # raw difference is -17 h
    assert s == 7.0


def test_half_hour_zones():
    assert hour_shift("Europe/London", "Asia/Kolkata", D) == 5.5


def test_dst_changes_the_shift():
    # US clocks changed on 8 Mar but UK clocks only on 29 Mar, so the gap is briefly 4 h, not 5 h
    assert hour_shift("Europe/London", "America/New_York", date(2026, 3, 20)) == -4.0
    assert hour_shift("Europe/London", "America/New_York", D) == -5.0


def test_east_is_slower_than_west_per_day():
    east, west = plan("Europe/London", "Asia/Tokyo", D), plan("Asia/Tokyo", "Europe/London", D)
    assert east["direction"] == "east" and west["direction"] == "west"
    assert east["rate_per_day"] == EAST_RATE < west["rate_per_day"] == WEST_RATE


def test_days_to_adjust_is_ceiling_of_shift_over_rate():
    p = plan("Europe/London", "Asia/Kolkata", D)
    assert p["days_to_adjust"] == 6  # 5.5 h at 1 h/day
    p = plan("Asia/Kolkata", "America/New_York", D)
    assert p["days_to_adjust"] == 7  # 10.5 h at 1.5 h/day


def test_schedule_ends_fully_shifted_and_never_overshoots():
    p = plan("Asia/Kolkata", "America/New_York", D)
    done = [r["shift_done"] for r in p["days"]]
    assert done == sorted(done) and done[-1] == abs(p["shift_hours"]) and max(done) <= abs(p["shift_hours"])


def test_last_row_matches_destination_bedtime():
    p = plan("Asia/Kolkata", "America/New_York", D, bed=23.0, wake=7.0)
    last = p["days"][-1]
    assert last["bedtime_dest"] == "23:00" and last["wake_dest"] == "07:00"


def test_rows_are_consecutive_days_with_flight_day_labelled():
    p = plan("Europe/London", "Asia/Tokyo", D, pre_days=3)
    days = [r["day"] for r in p["days"]]
    assert days == sorted(days) and p["days"][3]["label"] == "Flight day" and p["days"][3]["day"] == D.isoformat()


def test_no_shift_means_no_change():
    p = plan("Asia/Kolkata", "Asia/Kolkata", D)
    assert p["direction"] == "none" and all(r["bedtime"] == "23:00" for r in p["days"])


def test_validation():
    with pytest.raises(TripError):
        plan("Mars/Base", "Asia/Tokyo", D)
    with pytest.raises(TripError):
        plan("Asia/Tokyo", "Europe/London", D, pre_days=9)
    assert fmt(25.5) == "01:30" and fmt(-1.0) == "23:00"


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    z = c.get("/zones").json()
    assert "Asia/Kolkata" in z["popular"] and "Europe/London" in z["all"]
    body = {"origin": "Asia/Kolkata", "dest": "America/New_York", "flight_day": "2026-11-20"}
    r = c.post("/plan", json=body).json()
    assert r["direction"] == "west" and len(r["days"]) == 7 and c.get("/").status_code == 200


def test_api_validation():
    bad = {"origin": "Nope/Zone", "dest": "Asia/Tokyo", "flight_day": "2026-11-20"}
    assert c.post("/plan", json=bad).status_code == 422
    assert c.post("/plan", json={"origin": "Asia/Tokyo", "dest": "Asia/Tokyo", "flight_day": "x"}).status_code == 422
