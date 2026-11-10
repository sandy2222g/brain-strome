from __future__ import annotations

import numpy as np
import pandas as pd

from rentcheck.config import DISTRICTS, FEATURES, TARGET
from rentcheck.data import generate


def test_generate_is_deterministic_and_complete() -> None:
    a, b = generate(300, seed=1), generate(300, seed=1)
    pd.testing.assert_frame_equal(a, b)
    assert set(FEATURES + [TARGET]) <= set(a.columns)
    assert set(a["district"]) <= set(DISTRICTS)
    assert not a.isna().any().any()
    assert (a[TARGET] > 0).all()


def test_committed_data_shape(listings: pd.DataFrame) -> None:
    assert len(listings) == 4000
    assert listings["district"].nunique() == 8


def test_quantiles_are_ordered(model, listings) -> None:  # type: ignore[no-untyped-def]
    pred = model.predict_frame(listings.head(500))
    assert (pred["p10"] <= pred["p50"]).all()
    assert (pred["p50"] <= pred["p90"]).all()


def test_interval_coverage_near_target(model) -> None:  # type: ignore[no-untyped-def]
    cov = model.metrics["interval_coverage"]
    assert abs(cov - 0.8) < 0.06


def test_accuracy_is_reasonable(model) -> None:  # type: ignore[no-untyped-def]
    assert model.metrics["mape_pct"] < 12
    assert model.metrics["n_test"] == 800


def test_larger_flat_costs_more(model, flat) -> None:  # type: ignore[no-untyped-def]
    small = model.estimate_range({**flat, "size_m2": 40, "bedrooms": 1}).p50
    big = model.estimate_range({**flat, "size_m2": 95, "bedrooms": 3}).p50
    assert big > small


def test_central_district_costs_more_than_outer(model, flat) -> None:  # type: ignore[no-untyped-def]
    centre = model.estimate_range({**flat, "district": "Market Square"}).p50
    outer = model.estimate_range({**flat, "district": "Northgate"}).p50
    assert centre > outer


def test_metro_distance_lowers_rent(model, flat) -> None:  # type: ignore[no-untyped-def]
    near = model.estimate_range({**flat, "dist_metro_km": 0.2}).p50
    far = model.estimate_range({**flat, "dist_metro_km": 3.0}).p50
    assert near > far


def test_breakdown_adds_up(model, flat) -> None:  # type: ignore[no-untyped-def]
    bd = model.explain(flat)
    total = bd["typical_flat"] + sum(d["amount"] for d in bd["drivers"]) + bd["interactions"]
    assert np.isclose(total, bd["estimate"], atol=0.5)


def test_breakdown_sorted_by_size(model, flat) -> None:  # type: ignore[no-untyped-def]
    amounts = [abs(d["amount"]) for d in model.explain(flat)["drivers"]]
    assert amounts == sorted(amounts, reverse=True)


def test_district_table_ranked(model) -> None:  # type: ignore[no-untyped-def]
    rows = model.district_table()
    ppm = [r["median_per_m2"] for r in rows]
    assert len(rows) == 8
    assert ppm == sorted(ppm, reverse=True)
    assert rows[0]["district"] == "Market Square"


def test_save_and_load_roundtrip(model, flat, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from rentcheck.model import RentModel

    model.save(tmp_path / "m.joblib")
    again = RentModel.load(tmp_path / "m.joblib")
    assert again.estimate_range(flat) == model.estimate_range(flat)
