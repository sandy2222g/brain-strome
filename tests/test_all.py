from datetime import date

import pytest
from fastapi.testclient import TestClient

from eventparse.api import app
from eventparse.core import ParseError, load, parse

TODAY = date(2026, 11, 17)  # a Tuesday
D = load()
c = TestClient(app)


def test_tomorrow_with_pm_time():
    e = parse("Lunch with Maya tomorrow at 1pm", TODAY)
    assert (e["title"], e["date"], e["time"]) == ("Lunch with Maya", "2026-11-18", "13:00")


def test_next_weekday_is_in_the_following_week():
    assert parse("Dentist next Monday 9:30am", TODAY)["date"] == "2026-11-23"
    assert parse("Gym next Friday", TODAY)["date"] == "2026-11-27"


def test_plain_weekday_is_the_coming_one():
    assert parse("Meeting Friday 10am", TODAY)["date"] == "2026-11-20"
    assert parse("Meeting Tuesday 10am", TODAY)["date"] == "2026-11-24"  # same weekday means next week


def test_duration_in_hours_and_minutes():
    assert parse("Meeting Friday 10am for 2 hours", TODAY)["duration_min"] == 120
    assert parse("Dentist tomorrow for 45 minutes", TODAY)["duration_min"] == 45


def test_month_day_and_rollover_to_next_year():
    assert parse("Report on Dec 5 at 17:00", TODAY)["date"] == "2026-12-05"
    assert parse("Party Jan 3", TODAY)["date"] == "2027-01-03"
    assert parse("Party 3 January", TODAY)["date"] == "2027-01-03"


def test_relative_days_and_weeks():
    assert parse("Call in 3 days", TODAY)["date"] == "2026-11-20"
    assert parse("Review in 2 weeks", TODAY)["date"] == "2026-12-01"
    assert parse("Parcel day after tomorrow", TODAY)["date"] == "2026-11-19"


def test_noon_midnight_and_24h_times():
    assert parse("Call noon", TODAY)["time"] == "12:00"
    assert parse("Call midnight", TODAY)["time"] == "00:00"
    assert parse("Call 12am", TODAY)["time"] == "00:00" and parse("Call 12pm", TODAY)["time"] == "12:00"
    assert parse("Call at 17:45", TODAY)["time"] == "17:45"


def test_missing_parts_marked_incomplete():
    e = parse("Pick up parcel tomorrow", TODAY)
    assert e["time"] is None and not e["complete"]
    assert parse("Just a note", TODAY)["date"] is None


def test_every_sample_sentence_parses():
    events = [parse(s, TODAY) for s in D["sentences"]]
    assert all(e["date"] for e in events)
    assert sum(e["complete"] for e in events) == 6


def test_validation():
    with pytest.raises(ParseError):
        parse("   ", TODAY)
    with pytest.raises(ParseError):
        parse("Party on Feb 30", TODAY)
    with pytest.raises(ParseError):
        parse("Call 13pm", TODAY)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/parse", json={"sentences": body["sentences"], "today": body["today"]}).json()
    assert len(r["events"]) == 7 and r["events"][0]["date"] == "2026-11-18"
    assert c.get("/").status_code == 200
    assert c.post("/parse", json={"sentences": ["x"], "today": "bad"}).status_code == 422
