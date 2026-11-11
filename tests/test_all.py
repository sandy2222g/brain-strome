import itertools

import pytest
from fastapi.testclient import TestClient

from paintcans.api import app
from paintcans.core import (
    PaintError,
    Room,
    baseline_largest,
    baseline_smallest,
    cheapest_cans,
    litres_needed,
    wall_area,
)

CANS = {1.0: 9.0, 2.5: 20.0, 5.0: 34.0, 10.0: 60.0}
c = TestClient(app)


def test_wall_area_by_hand():
    assert wall_area(Room("r", 4, 3, 2.5, 5)) == 2 * 7 * 2.5 - 5


def test_no_wall_area_rejected():
    with pytest.raises(PaintError):
        wall_area(Room("r", 1, 1, 1, 99))


def test_litres():
    assert litres_needed([Room("r", 4, 3, 2.5, 5)], 2, 10) == pytest.approx(6.0)


def test_known_optimum():
    cost, counts = cheapest_cans(13.5, CANS)
    assert cost == 89 and counts == {10.0: 1, 2.5: 1, 1.0: 1}


def test_matches_brute_force():
    for litres in (0.5, 3, 7.5, 11, 13.5, 17):
        need = litres
        best = min(
            a * 9 + b * 20 + d * 34 + e * 60
            for a, b, d, e in itertools.product(range(19), range(8), range(5), range(3))
            if a + 2.5 * b + 5 * d + 10 * e >= need
        )
        assert cheapest_cans(litres, CANS)[0] == best


def test_never_worse_than_baselines():
    for litres in (1, 4.2, 9, 13.5, 26):
        opt = cheapest_cans(litres, CANS)[0]
        assert opt <= baseline_largest(litres, CANS)[0] and opt <= baseline_smallest(litres, CANS)[0]


def test_covers_the_need():
    for litres in (0.3, 6.1, 13.5, 22.2):
        _, counts = cheapest_cans(litres, CANS)
        assert sum(s * n for s, n in counts.items()) >= litres


def test_bad_cans():
    with pytest.raises(PaintError):
        cheapest_cans(3, {0.3: 5})


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert r["optimal"]["cost"] <= r["largest_only"]["cost"] and r["litres"] > 0
    assert c.get("/").status_code == 200


def test_api_validation():
    assert (
        c.post(
            "/plan",
            json={
                "coats": 9,
                "coverage": 10,
                "cans": {"1": 1},
                "rooms": [{"name": "a", "width": 3, "length": 3, "height": 2.5}],
            },
        ).status_code
        == 422
    )
