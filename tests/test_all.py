import pytest
from fastapi.testclient import TestClient

from rentest.api import app
from rentest.core import (
    FEATURES,
    RentError,
    baseline_metrics,
    evaluate,
    fit,
    load_rows,
    metrics,
    solve,
    split,
    trained,
)

c = TestClient(app)


def test_solve_by_hand():
    # 2x + y = 5 ; x + 3y = 10  ->  x = 1, y = 3
    assert solve([[2, 1], [1, 3]], [5, 10]) == pytest.approx([1.0, 3.0])
    with pytest.raises(RentError):
        solve([[1, 2], [2, 4]], [1, 2])


def test_recovers_an_exact_linear_rule():
    x = [[a, b, c_, d] for a in (30, 50, 80) for b in (1, 2) for c_ in (1, 5, 9) for d in (0, 20)]
    y = [10 * r[0] + 40 * r[1] - 20 * r[2] - 2 * r[3] + 100 for r in x]
    m = fit(x, y, lam=1e-9)
    assert m.per_unit()["area_m2"] == pytest.approx(10, abs=0.01)
    assert m.predict([60, 2, 3, 10]) == pytest.approx(10 * 60 + 80 - 60 - 20 + 100, abs=0.1)


def test_split_is_disjoint_and_complete():
    x, y = load_rows()
    xt, yt, xe, ye = split(x, y)
    assert len(xt) + len(xe) == len(x) == len(y) == 240 and len(xe) == 48 and len(yt) == 192


def test_held_out_accuracy():
    r = evaluate()
    assert r["model"]["r2"] > 0.95 and r["model"]["rmse"] < 70
    assert r["baseline"]["rmse"] > 4 * r["model"]["rmse"] and r["baseline"]["r2"] < 0.01


def test_coefficients_have_sensible_signs_and_size():
    u = evaluate()["per_unit"]
    assert 8 < u["area_m2"] < 10.5 and u["bedrooms"] > 30 and u["distance_km"] < -15 and u["age_years"] < -2


def test_monotonic_predictions():
    m = trained()
    assert m.predict([90, 2, 3, 10]) > m.predict([60, 2, 3, 10])
    assert m.predict([60, 2, 10, 10]) < m.predict([60, 2, 2, 10])


def test_metric_helpers():
    assert baseline_metrics([10, 20], [15, 15])["rmse"] == 0
    x, y = load_rows()
    assert metrics(fit(x, y), x, y)["r2"] > 0.95


def test_validation():
    with pytest.raises(RentError):
        fit([[1, 2, 3, 4]], [5])
    with pytest.raises(RentError):
        trained().predict([1, 2])
    assert len(FEATURES) == 4


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/estimate", json={"area_m2": 80, "bedrooms": 2, "distance_km": 4, "age_years": 10}).json()
    assert 950 < r["rent"] < 1150
    assert c.get("/metrics").json()["test"] == 48
    assert c.post("/estimate", json={"area_m2": 5, "bedrooms": 2, "distance_km": 4, "age_years": 10}).status_code == 422
    assert c.get("/").status_code == 200
