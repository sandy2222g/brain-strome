from datetime import date

import pytest
from fastapi.testclient import TestClient

from readpace.api import app
from readpace.core import PlanError, build, load, naive_pages_per_day, naive_total, plan, reading_days

RAW = load()
B = build(RAW)
c = TestClient(app)


def test_reading_days_skip_weekends():
    days = reading_days(B)
    assert len(days) == 20 and all(d.weekday() < 5 for d in days)


def test_plan_sums_to_pages_left():
    assert sum(p for _, p in plan(B)) == 600


def test_plan_is_even():
    pages = [p for _, p in plan(B)]
    assert max(pages) - min(pages) <= 1 and pages == [30] * 20


def test_extra_pages_go_to_earliest_days():
    b = build({**RAW, "pages": 645})
    pages = [p for _, p in plan(b)]
    assert pages[:5] == [31] * 5 and pages[5:] == [30] * 15


def test_naive_plan_falls_short():
    assert naive_pages_per_day(B) == 22 and naive_total(B) == 440 < 600


def test_no_rest_days_means_every_day():
    b = build({**RAW, "rest_weekdays": []})
    assert len(reading_days(b)) == 28


def test_single_day():
    b = build({**RAW, "deadline": RAW["start"], "rest_weekdays": []})
    assert plan(b) == [(date(2026, 11, 16), 600)]


def test_validation():
    with pytest.raises(PlanError):
        build({**RAW, "pages_read": 640})
    with pytest.raises(PlanError):
        build({**RAW, "deadline": "2026-01-01"})
    with pytest.raises(PlanError):
        build({"title": "x"})
    with pytest.raises(PlanError):
        plan(build({**RAW, "deadline": "2026-11-16", "rest_weekdays": [0]}))


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert r["reading_days"] == 20 and r["schedule"][0]["pages"] == 30 and r["naive_total"] == 440
    assert c.get("/").status_code == 200
    assert c.post("/plan", json={"title": "x"}).status_code == 422
