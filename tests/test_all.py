import pytest
from fastapi.testclient import TestClient

from parkfee.api import app
from parkfee.core import CarPark, ParkError, build, cheapest, fee, load

RAW = load()
CARS = build(RAW["carparks"])
c = TestClient(app)
STATION, MALL, COUNCIL = CARS


def test_fee_by_hand():
    assert fee(STATION, 30) == 4.0 and fee(STATION, 90) == 5.5 and fee(STATION, 180) == 7.0
    assert fee(MALL, 90) == 3.5


def test_part_hours_round_up():
    assert fee(STATION, 61) == fee(STATION, 120) == 5.5


def test_daily_cap_applies():
    assert fee(MALL, 600) == 15.0 and fee(COUNCIL, 600) == 9.0


def test_multi_day_caps_each_day():
    assert fee(COUNCIL, 1440 * 2) == 18.0
    assert fee(COUNCIL, 1441) == 9.0 + 2.5


def test_cheapest_changes_with_length():
    assert cheapest(CARS, 30)[0] == "Mall"
    assert cheapest(CARS, 600)[0] == "Council"


def test_fee_never_decreases_with_time():
    for car in CARS:
        fees = [fee(car, m) for m in range(1, 1500, 37)]
        assert fees == sorted(fees)


def test_tie_goes_to_alphabetical_name():
    twin = [CarPark("B", 2, 1, 5), CarPark("A", 2, 1, 5)]
    assert cheapest(twin, 60)[0] == "A"


def test_validation():
    with pytest.raises(ParkError):
        build([])
    with pytest.raises(ParkError):
        fee(STATION, 0)
    with pytest.raises(ParkError):
        build([{"name": "x", "first_hour": 5, "hourly": 1, "daily_cap": 2}])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/compare", json=c.get("/sample").json()).json()
    assert [x["best"] for x in r["rows"]] == ["Mall", "Mall", "Mall", "Council", "Council"]
    assert c.get("/").status_code == 200
    assert c.post("/compare", json={"carparks": [], "stays": [30]}).status_code == 422
