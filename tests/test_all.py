import itertools

import pytest
from fastapi.testclient import TestClient

from pizzaplan.api import app
from pizzaplan.core import PizzaError, cheapest, cheapest_slice_only, compare, feeds, load

D = load()
P, M, E, PCT = D["people"], D["menu"], D["slices_each"], D["meat_pct"]
c = TestClient(app)


def item(name: str, price: float, diet: str, slices: int = 8) -> dict[str, object]:
    return {"name": name, "price": price, "slices": slices, "diet": diet}


def test_sample_plan():
    r = cheapest(P, M, E, PCT)
    assert r["total"] == 65.0 and r["pizzas"] == 6 and r["spare_slices"] == 0
    assert {x["name"]: x["count"] for x in r["lines"]} == {"Pepperoni": 2, "Margherita": 2, "Veggie Supreme": 2}


def test_vegans_always_fed():
    r = cheapest(P, M, E, PCT)
    vegan_slices = sum(x["count"] * 8 for x in r["lines"] if x["name"] == "Veggie Supreme")
    assert vegan_slices >= P["vegan"] * E


def test_meat_share_changes_the_order():
    no_pref = cheapest(P, M, E, 0)
    assert no_pref["total"] == 60.0  # meat eaters just eat vegetarian pizza
    assert cheapest(P, M, E, 100)["total"] > cheapest(P, M, E, 60)["total"] > no_pref["total"]


def test_optimal_against_exhaustive_search():
    menu = [item("a", 7, "meat"), item("b", 6, "vegetarian", 6), item("c", 9, "vegan", 4)]
    people = {"meat": 3, "vegetarian": 2, "vegan": 2}
    clean = [{**m, "cents": round(m["price"] * 100)} for m in menu]  # type: ignore[operator]
    best = min(
        sum(n * m["cents"] for n, m in zip(cnt, clean, strict=True))
        for cnt in itertools.product(range(8), repeat=3)
        if feeds(list(cnt), clean, people, 2, 50)
    )
    assert cheapest(people, menu, 2, 50)["total"] * 100 == best


def test_naive_leaves_vegans_hungry():
    r = compare(P, M, E, PCT)
    assert r["naive"]["unfed_guests"] == 3 and r["naive"]["total"] == 54.0
    assert r["planned"]["total"] == 65.0
    assert "unfed_guests" not in r["planned"]


def test_naive_ok_when_menu_suits_everyone():
    assert cheapest_slice_only({"vegan": 2}, [item("v", 5, "vegan")], 2)["unfed_guests"] == 0


def test_validation():
    with pytest.raises(PizzaError):
        cheapest({"vegan": 2}, [item("m", 5, "meat")], 2)  # nothing a vegan can eat
    with pytest.raises(PizzaError):
        cheapest({}, M, 3)
    with pytest.raises(PizzaError):
        cheapest(P, M, 0)
    with pytest.raises(PizzaError):
        compare(P, M, 3, 150)
    with pytest.raises(PizzaError):
        cheapest({"alien": 2}, M, 3)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json={"slices_each": E, "meat_pct": PCT, "people": P, "menu": M}).json()
    assert r["planned"]["total"] == 65.0
    assert c.get("/").status_code == 200
    bad = {"slices_each": 3, "people": {"vegan": 1}, "menu": [item("m", 5, "meat")]}
    assert c.post("/plan", json=bad).status_code == 422
