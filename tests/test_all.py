import pytest
from fastapi.testclient import TestClient

from stockwise.api import app
from stockwise.core import Item, StockError, evaluate, load_demand, load_items, plan, simulate, z_score

c = TestClient(app)


def test_z_score_matches_known_values():
    assert z_score(0.5) == pytest.approx(0.0, abs=1e-9)
    assert z_score(0.95) == pytest.approx(1.6449, abs=1e-3)
    assert z_score(0.99) == pytest.approx(2.3263, abs=1e-3)


def test_plan_with_constant_demand_has_no_safety_stock():
    p = plan(Item("x", 30, 2, 1.0), [10] * 14)
    assert p["safety"] == 0 and p["reorder_point"] == 30.0  # 10/day x (2 lead + 1 review) days
    assert p["order_up_to"] == 50.0


def test_plan_safety_stock_by_hand():
    p = plan(Item("x", 30, 1, 1.0), [8, 12] * 7)  # mean 10, population sd 2, cover 2 days
    assert p["mean"] == 10 and p["sd"] == 2
    assert p["safety"] == pytest.approx(1.6449 * 2 * 2**0.5, abs=0.06)
    assert p["reorder_point"] == pytest.approx(20 + p["safety"], abs=0.06)


def test_shelf_life_caps_order_up_to_level():
    p = plan(Item("x", 2, 1, 1.0), [10] * 14)  # a 2-day shelf life: never hold more than 16 units
    assert p["order_up_to"] >= p["reorder_point"] and 16 <= p["order_up_to"] <= 20 + 1e-9


def test_stockout_counted_by_hand():
    r = simulate(Item("x", 100, 1, 1.0), [5] * 14, [100], "smart")
    assert r["short_days"] == 1 and r["short_units"] == 65  # opening stock is 35


def test_expiry_counted_by_hand():
    r = simulate(Item("x", 2, 1, 2.0), [5] * 14, [5, 5, 5], "weekly")
    assert r["waste_units"] >= 25 and r["waste_cost"] == r["waste_units"] * 2.0


def test_smart_beats_weekly_order_on_waste_and_shortages():
    t = evaluate()["totals"]
    assert t["smart"] == {"short_days": 2, "waste_cost": 103.4}
    assert t["weekly"] == {"short_days": 9, "waste_cost": 618.2}


def test_higher_service_level_means_fewer_shortages():
    assert evaluate(0.99)["totals"]["smart"]["short_days"] <= evaluate(0.95)["totals"]["smart"]["short_days"]


def test_data_files_and_validation():
    assert len(load_items()) == 5 and all(len(v) == 120 for v in load_demand().values())
    with pytest.raises(StockError):
        plan(Item("x", 5, 1, 1.0), [1] * 5)
    with pytest.raises(StockError):
        z_score(1.0)
    with pytest.raises(StockError):
        simulate(Item("x", 5, 1, 1.0), [3] * 14, [3], "magic")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/evaluation").json()
    assert len(r["items"]) == 5 and r["totals"]["smart"]["short_days"] == 2
    assert c.get("/evaluation", params={"service": 2}).status_code == 422
    assert c.get("/").status_code == 200
