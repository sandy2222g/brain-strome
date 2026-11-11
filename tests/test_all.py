import pytest
from fastapi.testclient import TestClient

from cookscale.api import app
from cookscale.core import CookError, combine, load, scale, shared_vs_separate, shopping_list, total, waste_value

packs, recipes = load()
c = TestClient(app)


def test_scale_linear():
    r = recipes["Lentil curry"]
    assert scale(r, 8)["lentils"] == 600 and scale(r, 2)["lentils"] == 150


def test_scale_rejects_zero():
    with pytest.raises(CookError):
        scale(recipes["Lentil curry"], 0)


def test_combine_sums_shared_items():
    both = combine([scale(recipes["Lentil curry"], 4), scale(recipes["Tomato egg rice"], 4)])
    assert both["tomato"] == 400 + 600


def test_rounds_up_to_whole_packs():
    lines = {x.item: x for x in shopping_list({"rice": 1001, "garlic": 10}, packs)}
    assert lines["rice"].packs == 2 and lines["garlic"].packs == 1


def test_exact_multiple_does_not_overbuy():
    assert shopping_list({"rice": 1000}, packs)[0].packs == 1


def test_on_hand_reduces_cost():
    full = total(shopping_list({"rice": 1500}, packs))
    less = total(shopping_list({"rice": 1500}, packs, {"rice": 600}))
    assert less < full
    assert shopping_list({"rice": 500}, packs, {"rice": 500})[0].packs == 0


def test_leftover_non_negative_and_consistent():
    for x in shopping_list(combine([scale(recipes["Spinach pasta"], 7)]), packs):
        assert x.leftover >= 0
        assert abs(x.packs * packs[x.item].size - x.needed - x.leftover) < 0.01


def test_waste_value_bounded_by_total():
    lines = shopping_list(scale(recipes["Lentil curry"], 5), packs)
    assert 0 <= waste_value(lines, packs) <= total(lines)


def test_combined_never_costs_more_than_separate():
    for n in (1, 3, 4, 9):
        comb, sep = shared_vs_separate(list(recipes.values()), n, packs)
        assert comb <= sep


def test_unknown_item():
    with pytest.raises(CookError):
        shopping_list({"saffron": 1}, packs)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/recipes").json()) == 3
    r = c.post("/shop", json={"recipes": ["Lentil curry", "Tomato egg rice"], "people": 6}).json()
    assert r["total"] > 0 and r["combined_cost"] <= r["separate_cost"]
    assert c.get("/").status_code == 200


def test_api_errors():
    assert c.post("/shop", json={"recipes": ["Nope"], "people": 2}).status_code == 422
    assert c.post("/shop", json={"recipes": ["Lentil curry"], "people": 0}).status_code == 422
