import pytest
from fastapi.testclient import TestClient

from menuplan.api import app
from menuplan.core import MenuError, list_order_plan, load, plan, violations

RAW = load()
D, DAYS = RAW["dishes"], RAW["days"]
c = TestClient(app)


def test_plan_has_no_violations():
    rows = plan(D, DAYS)
    assert len(rows) == 7 and violations(rows) == []


def test_plan_is_deterministic():
    assert plan(D, DAYS) == plan(list(reversed(D)), DAYS)


def test_no_repeated_dish_or_protein_run():
    rows = plan(D, DAYS)
    assert len({r["name"] for r in rows}) == 7
    assert all(a["protein"] != b["protein"] for a, b in zip(rows, rows[1:], strict=False))


def test_weeknights_are_quick():
    for r in plan(D, DAYS):
        if r["day"] not in ("Sat", "Sun"):
            assert r["minutes"] <= 30


def test_list_order_plan_breaks_rules():
    bad = violations(list_order_plan(D, DAYS))
    assert any("chicken two days running" in v for v in bad)
    assert any("Mon: Chicken curry takes 45 min" == v for v in bad)


def test_impossible_week_raises():
    # only two dishes fit a weeknight and they share a protein, so no plan exists
    dishes = [
        {"name": "A", "protein": "x", "minutes": 10},
        {"name": "B", "protein": "x", "minutes": 10},
        {"name": "C", "protein": "y", "minutes": 90},
    ]
    with pytest.raises(MenuError):
        plan(dishes, ["Mon", "Tue", "Wed"])


def test_weekend_allows_long_dish():
    dishes = [
        {"name": "A", "protein": "x", "minutes": 10},
        {"name": "B", "protein": "y", "minutes": 90},
    ]
    rows = plan(dishes, ["Mon", "Sat"])
    assert [r["name"] for r in rows] == ["A", "B"]


def test_validation():
    with pytest.raises(MenuError):
        plan(D, [])
    with pytest.raises(MenuError):
        plan(D[:2], DAYS)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert len(r["plan"]) == 7 and r["list_order_violations"]
    assert c.get("/").status_code == 200
    assert c.post("/plan", json={"dishes": [], "days": ["Mon"]}).status_code == 422
