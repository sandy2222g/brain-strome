import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bakeprice.api import app
from bakeprice.core import Curve, PricingError, Sale, best_price, cost_plus_price, fit, load, profit

HISTORY = load()
TRUTH = json.loads((Path(__file__).resolve().parents[1] / "data" / "truth.json").read_text())
c = TestClient(app)


def test_fit_recovers_an_exact_power_law():
    sales = [Sale(p, round(1000 * p**-1.5)) for p in (1, 2, 3, 4, 5, 6)]
    curve = fit(sales)
    assert curve.elasticity == pytest.approx(-1.5, abs=0.02) and curve.r2 > 0.999


def test_fitted_elasticities_are_close_to_the_hidden_truth():
    for name, (_, sales) in HISTORY.items():
        assert abs(fit(sales).elasticity - TRUTH[name]["elasticity"]) < 0.2


def test_best_price_formula_by_hand():
    # e=-2, cost=1: p* = 1 * -2 / (1-2) = 2
    curve = Curve(a=100, elasticity=-2, r2=1, low=0.5, high=10)
    assert best_price(curve, 1.0) == 2.0
    assert profit(curve, 1.0, 2.0) > profit(curve, 1.0, 1.5) and profit(curve, 1.0, 2.0) > profit(curve, 1.0, 3.0)


def test_inelastic_demand_goes_to_the_top_of_the_tried_range():
    assert best_price(Curve(100, -0.8, 1, 1, 6), 1.0) == 6


def test_price_never_leaves_the_observed_range():
    for _, (cost, sales) in HISTORY.items():
        curve = fit(sales)
        assert curve.low <= best_price(curve, cost) <= curve.high
        assert curve.low <= cost_plus_price(curve, cost) <= curve.high


def test_recommended_prices_earn_more_than_cost_plus_under_the_true_demand():
    tot_best = tot_base = 0.0
    for name, (cost, sales) in HISTORY.items():
        curve = fit(sales)
        t = TRUTH[name]
        truth = Curve(t["a"], t["elasticity"], 1, curve.low, curve.high)
        b, base = profit(truth, cost, best_price(curve, cost)), profit(truth, cost, cost_plus_price(curve, cost))
        assert b >= base - 1e-6
        tot_best, tot_base = tot_best + b, tot_base + base
    assert tot_best > 1.08 * tot_base and math.isfinite(tot_best)


def test_validation():
    with pytest.raises(PricingError):
        fit([Sale(1, 5), Sale(2, 4)])
    with pytest.raises(PricingError):
        fit([Sale(2, 5)] * 5)
    with pytest.raises(PricingError):
        fit([Sale(1, 5), Sale(2, 0), Sale(3, 2), Sale(4, 1)])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/price", json=body).json()
    assert len(r["items"]) == 5 and all(i["best_profit"] >= i["baseline_profit"] - 1e-6 for i in r["items"])
    assert len(r["items"][0]["curve"]) == 25
    assert c.get("/").status_code == 200


def test_api_validation():
    bad = {"items": [{"name": "x", "unit_cost": 1, "sales": [{"price": 2, "units": 3}]}]}
    assert c.post("/price", json=bad).status_code == 422
