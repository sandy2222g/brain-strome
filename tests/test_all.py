import pytest
from fastapi.testclient import TestClient

from hiketime.api import app
from hiketime.core import HikeError, estimate, fmt, legs, load, parse

T = load()
c = TestClient(app)


def test_first_leg_by_hand():
    first = legs(T["points"], 5.0, 10)[0]
    assert first["minutes"] == pytest.approx(25.2 + 5.0)  # 2.1 km at 5 km/h plus 50 m of climb


def test_descent_gets_no_credit_and_no_penalty():
    down = legs(T["points"], 5.0, 10)[-1]
    assert down["climb"] == 0 and down["minutes"] == pytest.approx(4.4 / 5 * 60)


def test_totals():
    r = estimate(T)
    assert r["total_km"] == 12.4 and r["total_climb"] == 760
    assert r["moving_min"] == pytest.approx(224.8, abs=0.1)
    assert r["rest_min"] == pytest.approx(r["moving_min"] / 60 * 5, abs=0.1)


def test_distance_only_underestimates():
    r = estimate(T)
    assert r["distance_only_min"] == pytest.approx(148.8, abs=0.1)
    assert r["underestimate_min"] == pytest.approx(94.7, abs=0.2)


def test_latest_start_leaves_a_margin_before_sunset():
    r = estimate(T)
    assert r["latest_start"] == "12:06"
    start = parse(r["latest_start"])
    assert start + r["total_min"] + 30 <= parse(T["sunset"]) + 1


def test_slower_pace_takes_longer():
    slow = {**T, "pace_kmh": 4.0}
    assert estimate(slow)["total_min"] > estimate(T)["total_min"]


def test_fmt_wraps_midnight():
    assert fmt(-30) == "23:30" and fmt(90) == "01:30"


def test_validation():
    with pytest.raises(HikeError):
        legs([{"name": "a", "km": 0, "height": 0}], 5, 10)
    with pytest.raises(HikeError):
        legs([{"name": "a", "km": 1, "height": 0}, {"name": "b", "km": 1, "height": 0}], 5, 10)
    with pytest.raises(HikeError):
        legs(T["points"], 0, 10)
    with pytest.raises(HikeError):
        parse("7pm")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = {k: v for k, v in c.get("/sample").json().items() if k != "note"}
    r = c.post("/estimate", json=body).json()
    assert r["total_min"] == pytest.approx(243.5, abs=0.1)
    assert c.get("/").status_code == 200
    assert c.post("/estimate", json={**body, "points": body["points"][:1]}).status_code == 422
