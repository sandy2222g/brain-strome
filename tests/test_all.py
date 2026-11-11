import pytest
from fastapi.testclient import TestClient

from boxpack.api import app
from boxpack.core import (
    Item,
    PackError,
    first_fit_decreasing,
    load,
    lower_bound,
    next_fit,
    optimal,
    validate,
)

KG, L, ITEMS = load()
NF = next_fit(KG, L, ITEMS)
FFD = first_fit_decreasing(KG, L, ITEMS)
OPT, PROVED = optimal(KG, L, ITEMS)
c = TestClient(app)


def names(boxes):
    return sorted(i.name for b in boxes for i in b.items)


def test_every_packing_contains_each_item_exactly_once():
    expected = sorted(i.name for i in ITEMS)
    for boxes in (NF, FFD, OPT):
        assert names(boxes) == expected


def test_no_box_exceeds_either_limit():
    for boxes in (NF, FFD, OPT):
        for b in boxes:
            assert b.kg <= KG + 1e-6 and b.litres <= L + 1e-6


def test_each_method_is_at_least_as_good_as_the_one_before():
    assert len(OPT) <= len(FFD) <= len(NF)


def test_sample_shows_real_gaps():
    assert (len(NF), len(FFD), len(OPT)) == (14, 11, 10)


def test_optimal_is_proved_and_meets_the_lower_bound_here():
    assert PROVED and len(OPT) == lower_bound(KG, L, ITEMS)


def test_lower_bound_is_never_beaten():
    assert min(len(NF), len(FFD), len(OPT)) >= lower_bound(KG, L, ITEMS)


def test_ffd_is_not_always_optimal():
    # classic trap: weights 4,4,3,3,3,3 into boxes of 10 with huge volume: FFD packs 4+4 | 3+3+3 | 3 (3 boxes)
    # but 4+3+3 | 4+3+3 needs only 2.
    items = [Item(f"i{k}", w, 1) for k, w in enumerate([4, 4, 3, 3, 3, 3])]
    assert len(first_fit_decreasing(10, 100, items)) == 3
    assert len(optimal(10, 100, items)[0]) == 2


def test_node_limit_returns_a_valid_unproved_packing():
    boxes, proved = optimal(KG, L, ITEMS, node_limit=1)
    assert not proved and names(boxes) == sorted(i.name for i in ITEMS)


def test_validation():
    with pytest.raises(PackError):
        validate(20, 60, [])
    with pytest.raises(PackError):
        validate(20, 60, [Item("anvil", 50, 5)])
    with pytest.raises(PackError):
        validate(20, 60, [Item("ghost", 0, 5)])
    with pytest.raises(PackError):
        optimal(20, 60, [Item(f"i{k}", 1, 1) for k in range(30)])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/pack", json={k: body[k] for k in ("box_kg", "box_litres", "items")}).json()
    assert (len(r["next_fit"]), len(r["first_fit_decreasing"]), len(r["optimal"])) == (14, 11, 10)
    assert r["proved_optimal"] and r["lower_bound"] == 10
    assert c.get("/").status_code == 200


def test_api_validation():
    bad = {"box_kg": 20, "box_litres": 60, "items": [{"name": "anvil", "kg": 50, "litres": 5}]}
    assert c.post("/pack", json=bad).status_code == 422
    assert c.post("/pack", json={"box_kg": 20, "box_litres": 60, "items": []}).status_code == 422
