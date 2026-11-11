import pytest
from fastapi.testclient import TestClient

from tilebox.api import app
from tilebox.core import TileError, boxes_needed, build, load, plan, tiles_for_floor

RAW = load()
J = build(RAW)
c = TestClient(app)


def test_floor_tiles_by_hand():
    assert tiles_for_floor(J) == 12 * 14 == 168


def test_waste_allowance():
    p = plan(J)
    assert p["tiles_with_waste"] == 194  # 168 x 1.15 = 193.2 -> 194


def test_boxes_round_up():
    assert boxes_needed(194, 11) == 18 and boxes_needed(198, 11) == 18 and boxes_needed(199, 11) == 19


def test_cost_and_spares():
    p = plan(J)
    assert p["boxes"] == 18 and p["cost"] == 18 * 38.5 and p["spare_tiles"] == 198 - 168


def test_diagonal_needs_at_least_as_much_as_straight():
    s = plan(build({**RAW, "layout": "straight"}))
    d = plan(build({**RAW, "layout": "diagonal"}))
    assert d["boxes"] >= s["boxes"]


def test_naive_plan_runs_short_in_some_case():
    j = build({**RAW, "layout": "straight", "tiles_per_box": 12})
    p = plan(j)  # floor 168 = exactly 14 boxes of 12, but 10% waste needs 185 tiles
    assert p["naive_boxes"] == 14 and p["naive_spare_after_cuts"] < 0 and p["boxes"] == 16


def test_exact_fit_room():
    j = build({**RAW, "width_m": 3.0, "length_m": 3.0})
    assert tiles_for_floor(j) == 100


def test_validation():
    with pytest.raises(TileError):
        build({"width_m": 3})
    with pytest.raises(TileError):
        build({**RAW, "layout": "spiral"})
    with pytest.raises(TileError):
        build({**RAW, "tile_cm": 0})


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/calc", json=c.get("/sample").json()).json()
    assert r["chosen"]["boxes"] == 18 and r["straight"]["boxes"] <= r["diagonal"]["boxes"]
    assert c.get("/").status_code == 200
    assert c.post("/calc", json={"width_m": 3}).status_code == 422
