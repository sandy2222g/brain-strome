import pytest
from fastapi.testclient import TestClient

from linepick.api import app
from linepick.core import Lane, LineError, build, eligible, fewest_people, load, rank, wait_seconds

RAW = load()
LANES = build(RAW["lanes"])
EXPRESS, A, B, SELF = LANES
c = TestClient(app)


def test_wait_by_hand():
    # Till B: ahead (8+6+5+12)=31 items *2 + 4 people *35, then me 14*2+35
    assert wait_seconds(B, 14) == 62 + 140 + 63 == 265


def test_more_people_can_still_be_faster():
    assert len(B.ahead) > len(A.ahead)
    assert wait_seconds(B, 14) < wait_seconds(A, 14)


def test_express_rejects_big_basket():
    assert not eligible(EXPRESS, 14) and eligible(EXPRESS, 10)
    assert rank(LANES, 14)[-1]["name"] == "Express"


def test_best_lane_and_baseline_differ():
    r = rank(LANES, 14)
    assert r[0]["name"] == "Till B"
    assert fewest_people(LANES, 14) == "Till A"


def test_small_basket_prefers_express():
    assert rank(LANES, 3)[0]["name"] == "Express"


def test_wait_grows_with_basket():
    waits = [wait_seconds(B, n) for n in range(1, 40)]
    assert waits == sorted(waits)


def test_tie_goes_to_name():
    twin = build(
        [
            {"name": "Z", "seconds_per_item": 2, "overhead": 10, "ahead": [3]},
            {"name": "Y", "seconds_per_item": 2, "overhead": 10, "ahead": [3]},
        ]
    )
    assert rank(twin, 5)[0]["name"] == "Y"
    assert isinstance(twin[0], Lane)


def test_validation():
    with pytest.raises(LineError):
        build([])
    with pytest.raises(LineError):
        wait_seconds(A, 0)
    with pytest.raises(LineError):
        build([{"name": "x", "seconds_per_item": 0, "overhead": 1, "ahead": []}])
    only_express = build([RAW["lanes"][0]])
    with pytest.raises(LineError):
        fewest_people(only_express, 50)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/pick", json={"lanes": body["lanes"], "items": body["items"]}).json()
    assert r["best"] == "Till B" and r["fewest_people"] == "Till A"
    assert r["extra_seconds_if_fewest_people"] == pytest.approx(342.5 - 265)
    assert c.get("/").status_code == 200
    assert c.post("/pick", json={"lanes": [], "items": 5}).status_code == 422
