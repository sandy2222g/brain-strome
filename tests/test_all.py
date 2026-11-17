from datetime import date

import pytest
from fastapi.testclient import TestClient

from cafecast.api import app
from cafecast.core import (
    SEASON,
    ForecastError,
    evaluate,
    fit,
    forecast,
    load,
    mae,
    plan_bakes,
    run,
    seasonal_naive,
)

c = TestClient(app)
DATES, Y = load()


def weekly(n: int, base: float = 50.0, step: float = 0.0) -> list[float]:
    pat = [0, 2, 4, 6, 20, 30, 10]
    return [base + step * i + pat[i % 7] for i in range(n)]


def test_perfect_pattern_is_recovered():
    y = weekly(42)
    _, state, sigma = fit(y)
    assert sigma < 0.5
    assert forecast(state, 7) == pytest.approx(y[:7], abs=1.0)


def test_trend_is_followed():
    y = weekly(56, step=1.0)
    _, state, _ = fit(y)
    nxt = forecast(state, 7)
    expected = [50 + 1.0 * (56 + k) + [0, 2, 4, 6, 20, 30, 10][k % 7] for k in range(7)]
    assert nxt == pytest.approx(expected, abs=2.5)


def test_one_step_errors_by_hand():
    # constant level, no season: the first prediction after the init season is the mean
    y = [10.0] * 21
    _, errs = run(y, 0.5, 0.1, 0.1)
    assert all(abs(e) < 1e-9 for e in errs) and len(errs) == 21 - SEASON


def test_beats_seasonal_naive_on_holdout():
    e = evaluate()
    assert e["mae_holdw"] == 7.41 and e["mae_naive"] == 10.07
    assert e["mae_holdw"] < e["mae_naive"]
    assert len(e["forecast"]) == len(e["actual"]) == len(e["naive"]) == 14 and len(e["dates"]) == len(Y)


def test_baseline_and_mae_helpers():
    assert seasonal_naive(list(range(14)), 3) == [7, 8, 9]
    assert mae([1, 2], [2, 4]) == 1.5


def test_bake_quantity_covers_forecast():
    p = plan_bakes(Y, DATES[-1])
    assert len(p["days"]) == 7 and p["days"][0]["date"] == "2026-05-11" and p["days"][0]["weekday"] == "Mon"
    assert all(d["bake"] > d["forecast"] for d in p["days"])
    assert max(p["days"], key=lambda d: d["forecast"])["weekday"] in {"Sat", "Sun"}


def test_validation():
    with pytest.raises(ForecastError):
        fit([1.0] * 10)
    with pytest.raises(ForecastError):
        fit([-1.0] * 30)
    with pytest.raises(ForecastError):
        plan_bakes(Y, date(2026, 1, 1), 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    s = c.get("/sample").json()
    r = c.post("/plan", json={"last_day": s["last_day"], "sold": s["sold"], "days": 5}).json()
    assert len(r["days"]) == 5 and r["sigma"] > 0
    assert c.get("/evaluation").json()["holdout_days"] == 14
    assert c.post("/plan", json={"last_day": "2026-01-01", "sold": [1, 2, 3]}).status_code == 422
    assert c.get("/").status_code == 200
