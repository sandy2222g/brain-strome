import pytest
from fastapi.testclient import TestClient

from farefair.api import app
from farefair.core import (
    FareError,
    Rider,
    alone_cost,
    build,
    distance_split,
    equal_split,
    load,
    shapley,
    total_fare,
)

RIDE = load()
SH = shapley(RIDE)
c = TestClient(app)


def test_two_riders_on_a_line_by_hand():
    # A alone costs 10, B alone 12, together 12. A joins first: A adds 10, then B adds 2; B first: B adds 12, A adds 0.
    # So A pays (10 + 0) / 2 = 5 and B pays (2 + 12) / 2 = 7.
    ride = build([Rider("A", (10, 0)), Rider("B", (12, 0))], (0, 0), 1.0)
    a, b = shapley(ride)
    assert total_fare(ride) == pytest.approx(12)
    assert a == pytest.approx(5.0) and b == pytest.approx(7.0)


def test_shares_add_up_to_the_real_fare():
    for split in (equal_split(RIDE), distance_split(RIDE), SH):
        assert sum(split) == pytest.approx(total_fare(RIDE))


def test_nobody_pays_more_than_riding_alone_under_shapley():
    for i, share in enumerate(SH):
        assert share <= alone_cost(RIDE, i) + 1e-9


def test_equal_split_makes_near_riders_subsidise_far_ones():
    over = [i for i, share in enumerate(equal_split(RIDE)) if share > alone_cost(RIDE, i) + 1e-9]
    assert [RIDE.riders[i].name for i in over] == ["Ana", "Ben"]


def test_the_rider_who_forces_the_detour_pays_most_under_shapley():
    assert max(range(len(SH)), key=lambda i: SH[i]) == 4  # Eli, stop at (4, 7)
    assert SH[4] > distance_split(RIDE)[4]  # the distance rule undercharges the detour


def test_identical_stops_pay_identically_and_a_rider_at_the_station_pays_nothing():
    ride = build([Rider("A", (5, 0)), Rider("B", (5, 0)), Rider("C", (0, 0))], (0, 0), 2.0)
    a, b, z = shapley(ride)
    assert a == pytest.approx(b) and z == pytest.approx(0)


def test_validation():
    with pytest.raises(FareError):
        build([], (0, 0), 1.0)
    with pytest.raises(FareError):
        build([Rider("A", (1, 1)), Rider("A", (2, 2))], (0, 0), 1.0)
    with pytest.raises(FareError):
        build([Rider("A", (1, 1))], (0, 0), 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/split", json=c.get("/sample").json()).json()
    assert r["total"] == pytest.approx(22.47, abs=0.01)
    assert r["over_alone"] == {"equal": 2, "distance": 0, "shapley": 0}
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/split", json={"rate_per_km": 1, "start": [0, 0], "riders": []}).status_code == 422
