from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from moonphase.api import app
from moonphase.core import (
    MoonError,
    age_days,
    error_hours,
    from_jd,
    full_moons_in,
    illumination,
    month_calendar,
    phase_name,
    reference,
    to_jd,
)

c = TestClient(app)


def test_julian_date_round_trip():
    assert to_jd(datetime(2000, 1, 1, 12)) == pytest.approx(2451545.0)
    t = datetime(2024, 5, 17, 3, 30)
    assert abs((from_jd(to_jd(t)) - t).total_seconds()) < 1


def test_reference_data():
    ref = reference()
    assert len(ref) == 12 and all(ref[i] < ref[i + 1] for i in range(11))
    assert all(29 <= (b - a).days <= 30 for a, b in zip(ref, ref[1:], strict=False))


def test_corrected_model_matches_published_full_moons():
    got = error_hours(True)
    assert max(got) < 0.75 and sum(got) / 12 < 0.3  # under 45 minutes worst case


def test_correction_is_a_real_improvement_over_the_mean_month():
    rough, good = error_hours(False), error_hours(True)
    assert sum(rough) / 12 > 5 and sum(good) * 15 < sum(rough)


def test_twelve_or_thirteen_full_moons_a_year():
    for y in (2023, 2024, 2025, 2026):
        assert len(full_moons_in(y)) in (12, 13)
    assert len(full_moons_in(2024)) == 12


def test_phase_at_known_moments():
    assert phase_name(datetime(2024, 1, 25, 17, 54)) == "Full moon"
    assert illumination(datetime(2024, 1, 25, 17, 54)) > 0.99
    assert illumination(datetime(2024, 1, 11, 11, 57)) < 0.01 and phase_name(datetime(2024, 1, 11, 12)) == "New moon"
    assert 0.35 < illumination(datetime(2024, 1, 18, 3, 52)) < 0.65  # first quarter: about half lit (see limitations)
    assert phase_name(datetime(2024, 1, 18, 3, 52)) == "First quarter"


def test_age_stays_inside_one_month_and_illumination_in_range():
    for d in range(0, 400, 7):
        t = datetime(2024, 1, 1, 12) + (datetime(2024, 1, 2) - datetime(2024, 1, 1)) * d
        assert 0 <= age_days(t) < 29.9 and 0 <= illumination(t) <= 1


def test_month_calendar():
    days = month_calendar(2024, 2)
    assert len(days) == 29 and days[0]["day"] == 1
    assert max(days, key=lambda d: d["illumination"])["day"] in (23, 24, 25)
    for bad in [(1800, 1), (2024, 13), (2024, 0)]:
        with pytest.raises(MoonError):
            month_calendar(*bad)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    m = c.get("/month", params={"year": 2024, "month": 1}).json()
    assert len(m["days"]) == 31 and m["first_weekday"] == 0 and m["full_moons"][0].startswith("2024-01-25")
    a = c.get("/accuracy").json()
    assert a["corrected"]["worst_hours"] < 0.75 < a["mean_only"]["worst_hours"]
    assert c.get("/month", params={"month": 13}).status_code == 422 and c.get("/").status_code == 200
