import pytest
from fastapi.testclient import TestClient

from sleepcycle.api import app
from sleepcycle.core import SleepError, bedtimes, eight_hour_bed, fixed_hours_check, fmt, parse

c = TestClient(app)


def test_parse_and_fmt_roundtrip():
    assert parse("06:45") == 405 and fmt(405) == "06:45" and fmt(-30) == "23:30"


def test_bedtimes_by_hand():
    got = {o["cycles"]: o["in_bed"] for o in bedtimes("06:45")}
    assert got == {6: "21:30", 5: "23:00", 4: "00:30", 3: "02:00"}


def test_sleep_hours():
    assert bedtimes("07:00")[0]["sleep_hours"] == 9.0


def test_options_sorted_earliest_bed_first_by_cycles_desc():
    assert [o["cycles"] for o in bedtimes("07:00")] == [6, 5, 4, 3]


def test_each_option_ends_on_cycle_boundary():
    for o in bedtimes("06:45", latency=20):
        chk = fixed_hours_check(o["in_bed"], "06:45", o["sleep_hours"], latency=20)
        assert not chk["mid_cycle"]


def test_eight_hours_lands_mid_cycle():
    bed = eight_hour_bed("06:45")
    chk = fixed_hours_check(bed, "06:45", 8.0)
    assert bed == "22:45" and chk["mid_cycle"] and chk["minutes_into_cycle"] == 15


def test_validation():
    for bad in ("25:00", "7", "ab:cd"):
        with pytest.raises(SleepError):
            parse(bad)
    with pytest.raises(SleepError):
        bedtimes("07:00", latency=-1)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json={"wake": "06:45"}).json()
    assert r["options"][1]["in_bed"] == "23:00" and r["eight_hour_bed"] == "22:45"
    assert c.post("/plan", json={"wake": "99:00"}).status_code == 422
    assert c.get("/").status_code == 200
