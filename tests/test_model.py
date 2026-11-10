from __future__ import annotations

import pytest

from carbon.calculator import calculate
from carbon.model import CarbonModel, percentile_rank
from carbon.schema import DETAILED_FIELDS
from conftest import make_answers


def skipped() -> dict[str, None]:
    return {name: None for name in DETAILED_FIELDS}


def test_percentile_rank_logic() -> None:
    ref = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(0.5, ref) == 0.0
    assert percentile_rank(2.5, ref) == 50.0
    assert percentile_rank(2.0, ref) == 37.5  # one below, one tie counted half
    assert percentile_rank(9.0, ref) == 100.0
    with pytest.raises(ValueError):
        percentile_rank(1.0, [])


def test_peer_percentile_rises_with_footprint(model: CarbonModel) -> None:
    low, mid, high = (model.peer_percentile(t, 2) for t in (4, 10, 24))
    assert 0 <= low < mid < high <= 100


def test_missing_answers_are_filled(model: CarbonModel) -> None:
    sparse = make_answers(**skipped())
    assert len(sparse.missing()) == 5
    full, filled = model.fill(sparse)
    assert full.missing() == [] and set(filled) == set(DETAILED_FIELDS)
    assert all(v >= 0 for v in filled.values())
    assert calculate(full).total_t > 0


def test_given_answers_are_never_overwritten(model: CarbonModel) -> None:
    partly = make_answers(electricity_kwh_month=None)
    full, filled = model.fill(partly)
    assert set(filled) == {"electricity_kwh_month"}
    assert full.car_km_week == 100 and full.waste_kg_week == 10
    same, nothing = model.fill(make_answers())
    assert nothing == {} and same == make_answers()


def test_fill_responds_to_household_size_and_mode(model: CarbonModel) -> None:
    big = model.fill(make_answers(**skipped(), household_size=5, home_size_m2=180))[1]
    small = model.fill(make_answers(**skipped(), household_size=1, home_size_m2=50))[1]
    assert big["electricity_kwh_month"] > small["electricity_kwh_month"]
    driver = model.fill(make_answers(**skipped(), commute_mode="car"))[1]
    walker = model.fill(make_answers(**skipped(), commute_mode="bike_walk"))[1]
    assert driver["car_km_week"] > walker["car_km_week"]


def test_estimate_has_ordered_band(model: CarbonModel) -> None:
    est = model.estimate(make_answers())
    assert 0 <= est["low_t"] <= est["tonnes"] <= est["high_t"]


def test_estimate_rises_with_flights(model: CarbonModel) -> None:
    few = model.estimate(make_answers(flights_short=0, flights_long=0))["tonnes"]
    many = model.estimate(make_answers(flights_short=8, flights_long=4))["tonnes"]
    assert many > few + 3


def test_held_out_metrics_are_sensible(model: CarbonModel) -> None:
    m = model.metrics
    assert m["footprint_r2"] > 0.85
    assert m["footprint_mae_t"] < m["baseline_mae_t"] / 2
    assert 0.7 <= m["band_coverage"] <= 0.95
    assert m["n_test"] >= 400 and set(m["imputer"]) == set(DETAILED_FIELDS)


def test_save_and_load_round_trip(model: CarbonModel, tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "m.joblib"
    model.save(path)
    again = CarbonModel.load(path)
    assert again.estimate(make_answers()) == model.estimate(make_answers())
