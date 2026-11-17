import pytest
from fastapi.testclient import TestClient

from busfind.api import app
from busfind.core import BusError, board, departures, fmt, load, next_departures, parse

RAW = load()
R12, R7, N3 = RAW["routes"]
c = TestClient(app)


def test_departures_count_and_ends():
    d = departures("05:30", "23:30", 20)
    assert fmt(d[0]) == "05:30" and fmt(d[-1]) == "23:30" and len(d) == 55


def test_after_midnight_route():
    d = departures("23:15", "04:15", 60)
    assert fmt(d[0]) == "23:15" and fmt(d[-1]) == "04:15" and len(d) == 6


def test_walk_time_skips_missed_bus():
    # 22:40 + 6 min walk = 22:46; route 7's last bus left at 22:45
    r = next_departures(R7, "22:40", 6)
    assert r["next"][0]["time"] == "06:00" and r["next"][0]["tomorrow"]


def test_catchable_without_walk():
    r = next_departures(R7, "22:40", 0)
    assert r["next"][0]["time"] == "22:45" and r["is_last"]


def test_next_three_for_12():
    r = next_departures(R12, "22:40", 6)
    assert [x["time"] for x in r["next"]] == ["22:50", "23:10", "23:30"]


def test_board_sorted_by_wait():
    rows = board(RAW["routes"], "22:40", 6)
    assert [r["route"] for r in rows] == ["12 Harbour", "N3 Night", "7 University"]


def test_just_after_midnight_uses_night_route():
    r = next_departures(N3, "00:10", 0)
    assert r["next"][0]["time"] == "00:15"


def test_validation():
    with pytest.raises(BusError):
        parse("24:00")
    with pytest.raises(BusError):
        departures("05:00", "06:00", 0)
    with pytest.raises(BusError):
        board([], "10:00")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/board", json={"routes": body["routes"], "now": body["now"], "walk_min": 6}).json()
    assert r["rows"][0]["route"] == "12 Harbour"
    assert c.get("/").status_code == 200
    assert c.post("/board", json={"routes": [], "now": "10:00"}).status_code == 422
