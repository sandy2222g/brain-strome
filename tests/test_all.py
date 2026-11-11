import pytest
from fastapi.testclient import TestClient

from seating.api import app
from seating.core import (
    FEUD_PENALTY,
    SeatingError,
    build,
    in_order,
    load,
    pairs_together,
    plan,
    score,
)

PARTY = load()
BASE = in_order(PARTY)
BEST = plan(PARTY)
c = TestClient(app)


def test_score_by_hand():
    p = build(["a", "b", "c", "d"], [["a", "b"], ["c", "d"]], [["a", "c"]], 2, 2)
    assert score(p, [["a", "b"], ["c", "d"]]) == 2
    assert score(p, [["a", "c"], ["b", "d"]]) == -FEUD_PENALTY
    assert score(p, [["a", "d"], ["b", "c"]]) == 0


def test_everyone_seated_once_within_table_size():
    for seating in (BASE, BEST):
        assert sorted(g for t in seating for g in t) == sorted(PARTY.guests)
        assert len(seating) <= PARTY.tables and all(len(t) <= PARTY.seats for t in seating)


def test_plan_beats_rsvp_order_by_a_wide_margin():
    assert score(PARTY, BEST) >= 5 * score(PARTY, BASE)
    assert (pairs_together(PARTY, BASE, "likes"), pairs_together(PARTY, BEST, "likes")) == (2, 15)


def test_plan_seats_no_feuding_pair_together():
    assert pairs_together(PARTY, BEST, "feuds") == 0


def test_plan_is_deterministic_for_a_seed():
    assert plan(PARTY, seed=0) == BEST


def test_feuds_are_kept_apart_even_when_friends_would_prefer_them_together():
    # a-b and a-c are friends but b-c feud: a table of three would score 2 - 10; planner must split them.
    p = build(["a", "b", "c", "d"], [["a", "b"], ["a", "c"]], [["b", "c"]], 2, 3)
    best = plan(p)
    assert pairs_together(p, best, "feuds") == 0 and score(p, best) >= 1


def test_validation():
    with pytest.raises(SeatingError):
        build(["a", "b"], [], [], 1, 1)  # not enough seats
    with pytest.raises(SeatingError):
        build(["a", "a"], [], [], 1, 2)
    with pytest.raises(SeatingError):
        build(["a", "b"], [["a", "z"]], [], 1, 2)
    with pytest.raises(SeatingError):
        build(["a", "b"], [["a", "a"]], [], 1, 2)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/seat", json={k: body[k] for k in ("guests", "likes", "feuds", "tables", "seats")}).json()
    assert r["planned"]["likes_together"] == 15 and r["in_order"]["likes_together"] == 2
    assert r["planned"]["feuds_together"] == 0 and r["likes_total"] == 20
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/seat", json={"guests": ["a", "b", "c"], "tables": 1, "seats": 2}).status_code == 422
