import pytest
from fastapi.testclient import TestClient

from seatpick.api import app
from seatpick.core import SeatError, best, blocks, first_free, load, mark, score

H = load()
R = H["rows"]
c = TestClient(app)


def test_best_block_by_hand():
    b = best(R, 3)
    assert (b["row"], b["start"]) == (4, 3) and b["score"] == 0.5


def test_first_free_is_the_front_corner():
    assert first_free(R, 3)["row"] == 0 and first_free(R, 3)["start"] == 0


def test_best_beats_first_free():
    assert best(R, 3)["score"] < first_free(R, 3)["score"]


def test_blocks_never_include_taken_seats():
    for b in blocks(R, 3):
        assert "X" not in R[b["row"]][b["start"] : b["start"] + 3]


def test_block_count_on_an_empty_row():
    assert len([b for b in blocks(["....."], 2)]) == 4


def test_no_block_returns_none():
    assert best(["X.X.X"], 2) is None and first_free(["X.X.X"], 2) is None


def test_mark_draws_party():
    m = mark(R, best(R, 3))
    assert m[4] == "XX.OOO..XX" and m[0] == R[0]


def test_ties_prefer_lower_row_then_left():
    rows = ["....", "....", "...."]
    b = best(rows, 2)
    assert b == min(blocks(rows, 2), key=lambda x: (x["score"], x["row"], x["start"]))


def test_validation():
    with pytest.raises(SeatError):
        best([], 2)
    with pytest.raises(SeatError):
        best(["..", "..."], 1)
    with pytest.raises(SeatError):
        best(["a."], 1)
    with pytest.raises(SeatError):
        best(["..."], 4)
    assert score(R, 4, 3, 3) == 0.5


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/pick", json={"rows": R, "party": 3}).json()
    assert r["best"]["row"] == 4 and r["map"][4] == "XX.OOO..XX"
    assert c.get("/").status_code == 200
    assert c.post("/pick", json={"rows": ["..", "."], "party": 1}).status_code == 422
