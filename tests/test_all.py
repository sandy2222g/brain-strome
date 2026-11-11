from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from gardenplan.api import app
from gardenplan.core import PlanError, build, conflicts, layout, load_crops, sowing_plan

LF, FF = date(2026, 4, 20), date(2026, 10, 25)
crops = load_crops()
c = TestClient(app)


def test_first_sowing_offset():
    s = sowing_plan(crops["Lettuce"], LF, FF)
    assert s[0].sow == LF - timedelta(weeks=4)


def test_succession_spacing_and_harvest_length():
    s = sowing_plan(crops["Radish"], LF, FF)
    assert len(s) > 3
    assert all((b.sow - a.sow).days == 14 for a, b in zip(s, s[1:], strict=False))
    assert all((x.harvest - x.sow).days == 28 for x in s)


def test_no_succession_gives_one_sowing():
    assert len(sowing_plan(crops["Tomato"], LF, FF)) == 1


def test_everything_harvested_before_first_frost():
    for cr in crops.values():
        assert all(s.harvest <= FF for s in sowing_plan(cr, LF, FF))


def test_cool_crops_stop_before_heat():
    hot = date(2026, 6, 15)
    s = sowing_plan(crops["Spinach"], LF, FF, hot)
    assert s and all(x.harvest <= hot for x in s)
    assert len(sowing_plan(crops["Spinach"], LF, FF)) > len(s)


def test_short_season_drops_long_crops():
    assert sowing_plan(crops["Onion"], LF, date(2026, 6, 1)) == []


def test_bad_frost_dates():
    with pytest.raises(PlanError):
        sowing_plan(crops["Peas"], FF, LF)


def test_conflicts_symmetric():
    assert conflicts(["Onion", "Peas", "Beans"], crops) == [("Beans", "Onion"), ("Onion", "Peas")]


def test_layout_separates_enemies():
    names = ["Onion", "Peas", "Beans", "Carrot", "Tomato", "Basil"]
    beds = layout(names, crops, 2)
    assert sorted(sum(beds, [])) == sorted(names)
    for bed in beds:
        assert conflicts(bed, crops) == []


def test_layout_groups_companions():
    beds = layout(["Tomato", "Basil", "Lettuce", "Radish"], crops, 2)
    assert any({"Tomato", "Basil"} <= set(b) for b in beds)


def test_layout_needs_a_bed():
    with pytest.raises(PlanError):
        layout(["Peas"], crops, 0)


def test_build_rejects_unknown_and_empty():
    with pytest.raises(PlanError):
        build(["Mango"], LF, FF, 1)
    with pytest.raises(PlanError):
        build([], LF, FF, 1)


def test_api_roundtrip():
    assert c.get("/health").json() == {"status": "ok"}
    assert "Tomato" in c.get("/crops").json()
    body = {"crops": ["Tomato", "Basil", "Peas"], "last_frost": "2026-04-20", "first_frost": "2026-10-25", "beds": 2}
    r = c.post("/plan", json=body).json()
    assert set(r["plan"]) == {"Tomato", "Basil", "Peas"} and len(r["layout"]) == 2


def test_api_errors():
    bad = {"crops": ["Mango"], "last_frost": "2026-04-20", "first_frost": "2026-10-25"}
    assert c.post("/plan", json=bad).status_code == 422
    swapped = {"crops": ["Peas"], "last_frost": "2026-10-25", "first_frost": "2026-04-20"}
    assert c.post("/plan", json=swapped).status_code == 422
    assert c.get("/").status_code == 200
