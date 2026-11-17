from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from cronexplain.api import app
from cronexplain.core import CronError, examples, explain, next_runs, parse

c = TestClient(app)
START = datetime(2026, 11, 17, 12, 0)  # a Tuesday


def fmt(runs: list[datetime]) -> list[str]:
    return [r.strftime("%Y-%m-%d %H:%M") for r in runs]


def test_field_parsing():
    p = parse("*/15 0-2,23 1,15 JAN-MAR 1-5")
    assert p.minute.values == {0, 15, 30, 45} and p.hour.values == {0, 1, 2, 23}
    assert p.dom.values == {1, 15} and p.month.values == {1, 2, 3} and p.dow.values == {1, 2, 3, 4, 5}
    assert parse("0 0 * * 7").dow.values == {0}  # 7 is Sunday too
    assert parse("5/20 * * * *").minute.values == {5, 25, 45}  # start/step runs to the end of the range


def test_next_runs_are_strictly_after_the_start():
    assert fmt(next_runs("*/15 * * * *", START, 3)) == ["2026-11-17 12:15", "2026-11-17 12:30", "2026-11-17 12:45"]
    assert fmt(next_runs("0 12 * * *", START, 2)) == ["2026-11-18 12:00", "2026-11-19 12:00"]


def test_weekday_schedule_skips_weekends():
    got = fmt(next_runs("30 9 * * 1-5", START, 5))
    assert got == ["2026-11-18 09:30", "2026-11-19 09:30", "2026-11-20 09:30", "2026-11-23 09:30", "2026-11-24 09:30"]


def test_day_of_month_and_weekday_both_set_means_either():
    # the 15th OR any Monday
    assert fmt(next_runs("0 9 15 * 1", START, 5)) == [
        "2026-11-23 09:00", "2026-11-30 09:00", "2026-12-07 09:00", "2026-12-14 09:00", "2026-12-15 09:00"]


def test_leap_day_and_impossible_dates():
    assert fmt(next_runs("0 0 29 2 *", START, 2)) == ["2028-02-29 00:00", "2032-02-29 00:00"]
    assert next_runs("0 0 31 2 *", START, 1) == []


def test_names_and_macros_match_numbers():
    assert fmt(next_runs("0 22 * * SUN", START, 2)) == fmt(next_runs("0 22 * * 0", START, 2))
    assert fmt(next_runs("@daily", START, 2)) == fmt(next_runs("0 0 * * *", START, 2))
    assert fmt(next_runs("@hourly", START, 1)) == ["2026-11-17 13:00"]


def test_plain_english():
    assert explain("30 9 * * 1-5") == "At 09:30 on Monday through Friday"
    assert explain("*/15 * * * *") == "Every 15 minutes"
    assert explain("0 9 1,15 * *") == "At 09:00 on days 1 and 15 of the month"
    assert explain("0 8,12,18 * * *") == "At 08:00, 12:00 and 18:00 every day"
    assert explain("0 0 29 2 *") == "At 00:00 on day 29 of the month in February"
    assert explain("0 9 15 * 1") == "At 09:00 on day 15 of the month or on Monday"
    assert explain("*/5 9-17 * * 1-5") == "Every 5 minutes, during hours 9 through 17 on Monday through Friday"


def test_every_example_parses_explains_and_runs():
    for e in examples():
        assert explain(e["expr"]) and next_runs(e["expr"], START, 1)


def test_validation_messages():
    for bad, msg in [("61 * * * *", "minute: 61"), ("* * * *", "expected 5 fields"), ("*/0 * * * *", "step"),
                     ("a * * * *", "not a number"), ("5-1 * * * *", "backwards"), ("0 25 * * *", "hour: 25"),
                     ("0 0 0 * *", "day of month: 0"), ("0 0 * 13 *", "month: 13")]:
        with pytest.raises(CronError, match=msg):
            parse(bad)
    with pytest.raises(CronError):
        next_runs("* * * * *", START, 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/explain", params={"expr": "30 9 * * 1-5", "n": 3}).json()
    assert r["meaning"] == "At 09:30 on Monday through Friday" and r["runs"][0] == "2026-11-18 09:30 Wed"
    assert c.get("/explain", params={"expr": "bogus"}).status_code == 422
    assert c.get("/explain", params={"expr": "* * * * *", "start": "not-a-date"}).status_code == 422
    assert len(c.get("/examples").json()["examples"]) == 8 and c.get("/").status_code == 200
