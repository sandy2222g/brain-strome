from itertools import combinations

import pytest
from fastapi.testclient import TestClient

from fixtures.api import app
from fixtures.core import (
    LeagueError,
    build,
    circle_schedule,
    count_breaks,
    home_counts,
    load,
    naive_schedule,
)

LEAGUE = load()
BAL = circle_schedule(LEAGUE)
NAIVE = naive_schedule(LEAGUE)
c = TestClient(app)


def team_names(n):
    return [f"T{i}" for i in range(n)]


def test_every_pair_plays_exactly_once_in_both_schedules():
    expected = {frozenset(p) for p in combinations(LEAGUE.teams, 2)}
    for sched in (BAL, NAIVE):
        games = [frozenset(g) for rd in sched for g in rd]
        assert len(games) == len(expected) and set(games) == expected


def test_each_team_plays_at_most_once_per_round_and_rounds_are_n_minus_1():
    assert len(BAL) == len(LEAGUE.teams) - 1
    for rd in BAL:
        teams = [t for g in rd for t in g]
        assert len(teams) == len(set(teams)) == len(LEAGUE.teams)


def test_balanced_schedule_reaches_the_minimum_n_minus_2_breaks():
    assert count_breaks(BAL) == len(LEAGUE.teams) - 2 == 6
    for n in (4, 6, 10, 12):
        assert count_breaks(circle_schedule(build("x", team_names(n)))) == n - 2


def test_naive_schedule_is_much_worse():
    assert count_breaks(NAIVE) == 30
    assert sorted(home_counts(NAIVE).values()) == list(range(8))  # one team home 7 times, another never


def test_balanced_home_games_differ_by_at_most_one():
    counts = home_counts(BAL).values()
    assert max(counts) - min(counts) <= 1


def test_odd_number_of_teams_gives_byes_and_still_plays_every_pair_once():
    league = build("x", team_names(7))
    sched = circle_schedule(league)
    games = [frozenset(g) for rd in sched for g in rd]
    assert len(games) == 21 and len(set(games)) == 21
    assert all(len(rd) == 3 for rd in sched)  # one team sits out each round


def test_validation():
    with pytest.raises(LeagueError):
        build("x", ["a"])
    with pytest.raises(LeagueError):
        build("x", ["a", "a"])
    with pytest.raises(LeagueError):
        build("x", ["a", "BYE"])
    with pytest.raises(LeagueError):
        build("x", ["a", " "])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/schedule", json=c.get("/sample").json()).json()
    assert r["balanced"]["breaks"] == 6 and r["naive"]["breaks"] == 30 and r["balanced"]["home_spread"] <= 1
    assert len(r["balanced"]["rounds"]) == 7 and c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/schedule", json={"teams": ["only"]}).status_code == 422
