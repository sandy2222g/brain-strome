import pytest
from fastapi.testclient import TestClient

from goldenhour.api import app
from goldenhour.core import SunError, elevation, load, plan, rule_of_thumb, sun_declination_eqtime

D = load()
P = {p["name"]: p for p in D["places"]}
DAY = D["date"]
c = TestClient(app)


def minutes(s: str) -> int:
    h, m = s.split(" ")[0].split(":")
    return int(h) * 60 + int(m)


def at(name: str) -> dict:
    p = P[name]
    return plan(DAY, p["lat"], p["lon"], p["tz"])


@pytest.mark.parametrize(
    ("name", "rise", "set_"),
    [
        ("London", "04:43", "21:21"),
        ("New York", "05:25", "20:31"),
        ("Mumbai", "06:02", "19:19"),
        ("Sydney", "07:00", "16:54"),
    ],
)
def test_matches_published_times_within_two_minutes(name, rise, set_):
    r = at(name)
    assert abs(minutes(r["sunrise"]) - minutes(rise)) <= 2
    assert abs(minutes(r["sunset"]) - minutes(set_)) <= 2


def test_solstice_declination_and_equinox_noon():
    decl, _ = sun_declination_eqtime(1782043200)  # 2026-06-21 12:00 UTC
    assert abs(decl * 57.2958 - 23.44) < 0.1
    assert elevation(1774008000 + 7 * 60, 0.0, 0.0) > 85  # solar noon, 2026-03-20, equator, lon 0


def test_golden_hour_windows_are_ordered():
    r = at("London")
    assert minutes(r["morning_golden"][0]) == minutes(r["sunrise"]) < minutes(r["morning_golden"][1])
    assert minutes(r["evening_golden"][0]) < minutes(r["evening_golden"][1]) == minutes(r["sunset"])
    assert minutes(r["evening_blue"][0]) >= minutes(r["sunset"])


def test_polar_day_and_midnight_sunset():
    t = at("Tromso")
    assert t["status"] == "polar day" and t["sunrise"] is None and t["daylight_minutes"] is None
    r = at("Reykjavik")
    assert r["sunset"].endswith("(+1)") and 1250 < r["daylight_minutes"] < 1290
    assert r["evening_blue"] is None  # the sun never gets low enough


def test_polar_night():
    assert plan("2026-12-21", 78.2, 15.6, 1)["status"] == "polar night"


def test_southern_winter_is_shorter():
    assert at("Sydney")["daylight_minutes"] < 650 < at("London")["daylight_minutes"]


def test_rule_of_thumb_error():
    r = rule_of_thumb(DAY, P["London"]["lat"], P["London"]["lon"], 1)
    assert (r["sunrise_error_min"], r["sunset_error_min"]) == (77, 202)
    assert rule_of_thumb(DAY, 69.6, 18.9, 2)["sunrise_error_min"] is None


def test_validation():
    for args in (("not-a-date", 0, 0, 0), (DAY, 95, 0, 0), (DAY, 0, 200, 0), (DAY, 0, 0, 20)):
        with pytest.raises(SunError):
            plan(*args)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = {"date": DAY, "lat": 51.5074, "lon": -0.1278, "tz": 1}
    r = c.post("/plan", json=body).json()
    assert r["plan"]["sunrise"] == "04:43" and r["rule_of_thumb"]["sunset_error_min"] == 202
    assert c.get("/").status_code == 200
    assert c.post("/plan", json={**body, "lat": 99}).status_code == 422
