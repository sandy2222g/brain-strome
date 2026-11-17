import pytest
from fastapi.testclient import TestClient

from powercost.api import app
from powercost.core import PowerError, cost, kwh_per_month, load, report

H = load()
T = H["tariff"]
A = {a["name"]: a for a in H["appliances"]}
c = TestClient(app)


def test_kwh_by_hand():
    assert kwh_per_month(A["Dishwasher"], 30) == pytest.approx(54.0)  # 1.8 kW * 1 h * 30
    assert kwh_per_month(A["Fridge"], 30) == pytest.approx(86.4)


def test_cost_by_hand():
    # dishwasher: 54 kWh, 90% peak
    assert cost(A["Dishwasher"], 30, T) == pytest.approx(54 * (0.9 * 0.34 + 0.1 * 0.14), abs=0.01)


def test_shifting_only_affects_shiftable():
    assert cost(A["Fridge"], 30, T, shifted=True) == cost(A["Fridge"], 30, T)
    assert cost(A["EV charger"], 30, T, shifted=True) < cost(A["EV charger"], 30, T)


def test_shifted_cost_is_off_peak_rate():
    assert cost(A["Dishwasher"], 30, T, shifted=True) == pytest.approx(54 * 0.14, abs=0.01)


def test_report_sorted_and_totals():
    r = report(H)
    assert [x["cost"] for x in r["rows"]] == sorted((x["cost"] for x in r["rows"]), reverse=True)
    assert r["total"] == pytest.approx(sum(x["cost"] for x in r["rows"]))
    assert r["total_saving"] == pytest.approx(sum(x["saving"] for x in r["rows"]))
    assert r["total_saving"] > 0


def test_flat_rate_misses_the_pattern():
    r = {x["name"]: x for x in report(H)["rows"]}
    assert r["Fridge"]["flat_cost"] > r["Fridge"]["cost"]  # a mostly off-peak load is cheaper than the flat average
    assert r["Electric oven"]["flat_cost"] < r["Electric oven"]["cost"]  # all-peak load is dearer


def test_validation():
    with pytest.raises(PowerError):
        kwh_per_month({"name": "x", "watts": 0, "hours_per_day": 1, "peak_share": 0.5}, 30)
    with pytest.raises(PowerError):
        kwh_per_month({"name": "x", "watts": 5, "hours_per_day": 25, "peak_share": 0.5}, 30)
    with pytest.raises(PowerError):
        report({**H, "appliances": []})


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/report", json=c.get("/sample").json()).json()
    assert r["total"] > 0 and r["rows"][0]["name"] == "EV charger"
    assert c.get("/").status_code == 200
    empty = {"tariff": {"peak": 1, "off_peak": 1, "flat": 1}, "appliances": []}
    assert c.post("/report", json=empty).status_code == 422
