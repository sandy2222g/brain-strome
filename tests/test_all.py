import pytest
from fastapi.testclient import TestClient

from albumgroup.api import app
from albumgroup.core import AlbumError, group_by_day, group_by_gap, load

RAW = load()
P = RAW["photos"]
c = TestClient(app)


def test_five_albums_at_four_hours():
    a = group_by_gap(P, 4)
    assert [x["count"] for x in a] == [8, 7, 1, 4, 3]
    assert len(a) == 5


def test_midnight_party_stays_together():
    first = group_by_gap(P, 4)[0]
    assert first["start"] == "2026-10-03T19:05" and first["end"] == "2026-10-04T01:05"


def test_by_day_splits_the_party():
    days = group_by_day(P)
    assert len(days) == 6
    assert days[0]["count"] == 5 and days[1]["count"] == 3


def test_every_photo_in_exactly_one_album():
    a = group_by_gap(P, 4)
    files = [f for x in a for f in x["files"]]
    assert sorted(files) == sorted(p["file"] for p in P) and len(files) == len(set(files))


def test_gap_is_strictly_greater_than():
    pair = [{"file": "a", "taken": "2026-01-01T10:00"}, {"file": "b", "taken": "2026-01-01T14:00"}]
    assert len(group_by_gap(pair, 4)) == 1
    assert len(group_by_gap(pair, 3.9)) == 2


def test_unsorted_input_is_sorted():
    shuffled = list(reversed(P))
    assert [x["count"] for x in group_by_gap(shuffled, 4)] == [8, 7, 1, 4, 3]


def test_validation():
    with pytest.raises(AlbumError):
        group_by_gap([], 4)
    with pytest.raises(AlbumError):
        group_by_gap(P, 0)
    with pytest.raises(AlbumError):
        group_by_gap([{"file": "a", "taken": "yesterday"}], 4)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/group", json={"photos": P, "gap_hours": 4}).json()
    assert len(r["albums"]) == 5 and r["by_day_count"] == 6
    assert c.get("/").status_code == 200
    assert c.post("/group", json={"photos": [], "gap_hours": 4}).status_code == 422
