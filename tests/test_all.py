import pytest
from fastapi.testclient import TestClient

from unitprice.api import app
from unitprice.core import PriceError, largest_pack, load, per_100, rank

P = load()["products"]
c = TestClient(app)


def test_per_100_by_hand():
    assert per_100(P[0])[1] == pytest.approx(0.24)
    assert per_100(P[1])[1] == pytest.approx(0.27)
    assert per_100(P[2])[1] == pytest.approx(0.27)


def test_imperial_units_converted():
    assert per_100(P[3])[1] == pytest.approx(2.10 / (2 * 453.592) * 100)
    assert per_100(P[4])[1] == pytest.approx(1.20 / (12 * 28.3495) * 100)


def test_ranking_order_and_best():
    rows = rank(P)
    assert rows[0]["name"] == "Rice 2 lb pack"
    assert [r["per_100"] for r in rows] == sorted(r["per_100"] for r in rows)
    assert rows[0]["extra_pct"] == 0


def test_biggest_pack_is_not_cheapest():
    assert largest_pack(P) == "Rice 5 kg sack"
    assert rank(P)[0]["name"] != largest_pack(P)


def test_extra_pct():
    rows = {r["name"]: r for r in rank(P)}
    assert rows["Rice 5 kg sack"]["extra_pct"] == pytest.approx(16.6, abs=0.1)


def test_volume_units():
    milk = [
        {"name": "A", "price": 1.0, "qty": 1, "unit": "l"},
        {"name": "B", "price": 0.6, "qty": 500, "unit": "ml"},
    ]
    assert rank(milk)[0]["name"] == "A"


def test_validation():
    with pytest.raises(PriceError):
        rank([])
    with pytest.raises(PriceError):
        per_100({"name": "x", "price": 1, "qty": 1, "unit": "stone"})
    with pytest.raises(PriceError):
        per_100({"name": "x", "price": 0, "qty": 1, "unit": "g"})
    with pytest.raises(PriceError):
        rank([{"name": "a", "price": 1, "qty": 1, "unit": "g"}, {"name": "b", "price": 1, "qty": 1, "unit": "ml"}])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/compare", json=c.get("/sample").json()).json()
    assert r["best"] == "Rice 2 lb pack" and r["largest"] == "Rice 5 kg sack"
    assert c.get("/").status_code == 200
    assert c.post("/compare", json={"products": []}).status_code == 422
