from datetime import date

import pytest
from fastapi.testclient import TestClient

from bdaycount.api import app
from bdaycount.core import BirthdayError, calendar_order, load, next_birthday, occurrence, parse, upcoming

RAW = load()
TODAY = parse(RAW["today"])
c = TestClient(app)


def test_birthday_today_is_zero_days():
    r = upcoming([{"name": "C", "born": "1998-11-17"}], TODAY)[0]
    assert r["days"] == 0 and r["turning"] == 28


def test_passed_birthday_rolls_to_next_year():
    assert next_birthday(date(2002, 6, 15), TODAY) == date(2027, 6, 15)


def test_leap_day_in_non_leap_year():
    assert occurrence(date(2000, 2, 29), 2027) == date(2027, 2, 28)
    assert occurrence(date(2000, 2, 29), 2028) == date(2028, 2, 29)


def test_leap_day_person_in_sample():
    ben = next(r for r in upcoming(RAW["people"], TODAY) if r["name"] == "Ben")
    assert ben["date"] == "2027-02-28" and ben["turning"] == 27


def test_sorted_by_days_then_name():
    rows = upcoming(RAW["people"], TODAY)
    assert [r["name"] for r in rows][:3] == ["Chloe", "Dev", "Elif"]
    assert [r["days"] for r in rows] == sorted(r["days"] for r in rows)


def test_calendar_order_differs():
    assert calendar_order(RAW["people"])[0] == "Asha"
    assert upcoming(RAW["people"], TODAY)[0]["name"] == "Chloe"


def test_year_end_rollover():
    assert next_birthday(date(1990, 1, 2), date(2026, 12, 30)) == date(2027, 1, 2)


def test_validation():
    with pytest.raises(BirthdayError):
        parse("17/11/2026")
    with pytest.raises(BirthdayError):
        next_birthday(date(2030, 1, 1), TODAY)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/upcoming", json=c.get("/sample").json()).json()
    assert r["rows"][0]["name"] == "Chloe"
    assert c.get("/").status_code == 200
    assert c.post("/upcoming", json={"today": "x", "people": [{"name": "a", "born": "2000-01-01"}]}).status_code == 422
