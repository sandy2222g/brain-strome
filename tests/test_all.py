import random
from itertools import combinations

import pytest
from fastapi.testclient import TestClient

from bracketmaker.api import app
from bracketmaker.core import (
    BracketError,
    Team,
    bracket_size,
    first_round,
    load_teams,
    round_robin,
    run_knockout,
    seed_order,
    simulate,
    win_prob,
)

c = TestClient(app)
T = load_teams()


def test_standard_seed_orders():
    assert seed_order(2) == [1, 2]
    assert seed_order(4) == [1, 4, 2, 3]
    assert seed_order(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    for bad in (0, 1, 3, 6, 12):
        with pytest.raises(BracketError):
            seed_order(bad)


def test_every_round_pairs_seeds_summing_to_size_plus_one():
    for size in (4, 8, 16, 32):
        o = seed_order(size)
        assert sorted(o) == list(range(1, size + 1))
        assert all(o[i] + o[i + 1] == size + 1 for i in range(0, size, 2))


def test_top_two_seeds_can_only_meet_in_the_final():
    for size in (4, 8, 16):
        o = seed_order(size)
        half = size // 2
        assert o.index(1) < half <= o.index(2)  # opposite halves of the draw


def test_byes_go_to_the_top_seeds():
    pairs = first_round(T[:6])  # 6 teams -> 8 slots -> 2 byes
    assert bracket_size(6) == 8 and len(pairs) == 4
    byes = [p for p in pairs if None in p]
    assert len(byes) == 2 and {(p[0] or p[1]).name for p in byes} == {T[0].name, T[1].name}  # type: ignore[union-attr]


def test_win_probability():
    a, b = Team("a", 1400), Team("b", 1000)
    assert win_prob(a, b) == pytest.approx(10 / 11, abs=1e-3) and win_prob(a, a) == 0.5
    assert win_prob(a, b) + win_prob(b, a) == pytest.approx(1)


def test_round_robin_every_pair_exactly_once():
    for n in (2, 5, 8, 12):
        teams = T[:n] if n <= 12 else T
        rounds = round_robin(teams)
        games = [frozenset((a.name, b.name)) for r in rounds for a, b in r]
        assert len(games) == len(set(games)) == n * (n - 1) // 2
        assert set(games) == {frozenset((a.name, b.name)) for a, b in combinations(teams, 2)}
        for r in rounds:  # nobody plays twice in one round
            names = [t.name for g in r for t in g]
            assert len(names) == len(set(names))


def test_knockout_always_returns_a_participant_and_favourites_win_more():
    rng = random.Random(3)
    pairs = first_round(T[:5])
    wins = {t.name: 0 for t in T[:5]}
    for _ in range(600):
        wins[run_knockout(pairs, rng).name] += 1
    assert sum(wins.values()) == 600 and wins[T[0].name] > wins[T[4].name]


def test_formats_rank_by_how_often_the_best_team_wins():
    s = simulate(T, 5000, seed=2)
    best = T[0].name
    assert s["round_robin"][best] > s["seeded"][best] > s["random"][best]
    assert abs(sum(s["seeded"].values()) - 1) < 0.01 and s["seeded"][T[-1].name] < 0.01
    with pytest.raises(BracketError):
        simulate(T, 5)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    b = c.get("/bracket", params={"n": 12}).json()
    assert b["size"] == 16 and len(b["first_round"]) == 8 and sum(len(r) for r in b["round_robin"]) == 66
    s = c.get("/simulate", params={"n": 12, "trials": 2000}).json()["chances"]
    assert set(s) == {"seeded", "random", "round_robin"}
    assert c.get("/bracket", params={"n": 1}).status_code == 422
    assert c.get("/simulate", params={"trials": 5}).status_code == 422
    assert c.get("/").status_code == 200 and len(c.get("/teams").json()["teams"]) == 12
