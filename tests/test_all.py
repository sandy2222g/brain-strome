import pytest
from fastapi.testclient import TestClient

from chorerota.api import app
from chorerota.core import (
    Chore,
    Person,
    RotaError,
    effort_spread,
    fair_rota,
    load,
    round_robin,
    total_dislike,
    validate,
    worst_streak,
)

PEOPLE, CHORES = load()
WEEKS = 8
FAIR = fair_rota(PEOPLE, CHORES, WEEKS)
RR = round_robin(PEOPLE, CHORES, WEEKS)
c = TestClient(app)


def test_every_week_gives_each_chore_to_a_different_person():
    for rota in (FAIR, RR):
        assert len(rota) == WEEKS
        for week in rota:
            assert len(week) == len(CHORES) and len(set(week)) == len(week)


def test_fair_rota_is_much_less_disliked_than_round_robin():
    assert total_dislike(FAIR, PEOPLE, CHORES) < 0.75 * total_dislike(RR, PEOPLE, CHORES)


def test_fair_rota_stays_reasonably_balanced():
    total = WEEKS * sum(ch.effort for ch in CHORES)
    assert effort_spread(FAIR, CHORES, len(PEOPLE)) <= 0.05 * total


def test_round_robin_is_perfectly_balanced_over_full_cycles():
    assert effort_spread(RR, CHORES, len(PEOPLE)) == 0


def test_higher_balance_never_widens_the_spread_on_the_sample():
    low = effort_spread(fair_rota(PEOPLE, CHORES, WEEKS, balance=0), CHORES, len(PEOPLE))
    high = effort_spread(fair_rota(PEOPLE, CHORES, WEEKS, balance=20), CHORES, len(PEOPLE))
    assert high < low


def test_zero_balance_picks_everyones_cheapest_assignment_each_week():
    only_dislike = fair_rota(PEOPLE, CHORES, 1, balance=0)
    assert (
        total_dislike(only_dislike, PEOPLE, CHORES) == 4
    )  # Sam-Bins, Priya-Hoovering, Joe-Kitchen, Mei-Bathroom: 1 each, checked by hand


def test_same_chore_streak_is_short():
    assert worst_streak(FAIR) <= 2 and worst_streak(RR) == 1


def test_validation():
    with pytest.raises(RotaError):
        validate(PEOPLE, CHORES, 0)
    with pytest.raises(RotaError):
        validate(PEOPLE[:2], CHORES, 4)
    with pytest.raises(RotaError):
        validate([Person("a", {})], [Chore("x", 1)], 4)
    with pytest.raises(RotaError):
        validate([Person("a", {"x": 3}), Person("a", {"x": 3})], [Chore("x", 1)], 4)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/rota", json={"people": body["people"], "chores": body["chores"], "weeks": 8}).json()
    assert r["fair"]["dislike"] < r["round_robin"]["dislike"]
    assert len(r["fair"]["weeks"]) == 8 and r["chores"] == ["Bins", "Bathroom", "Kitchen", "Hoovering"]
    assert c.get("/").status_code == 200


def test_api_validation():
    body = c.get("/sample").json()
    bad = {"people": body["people"][:2], "chores": body["chores"], "weeks": 4}
    assert c.post("/rota", json=bad).status_code == 422
