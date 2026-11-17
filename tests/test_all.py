import random
from itertools import combinations

import pytest
from fastapi.testclient import TestClient

from teampick.api import app
from teampick.core import TeamError, broken_rules, load, split, top_two_picks

D = load()
P, APART, TOGETHER = D["players"], D["keep_apart"], D["keep_together"]
c = TestClient(app)


def brute_gap(players, apart=(), together=()):
    names = [p["name"] for p in players]
    skill = {p["name"]: p["skill"] for p in players}
    best = None
    for combo in combinations(names, len(names) // 2):
        a = set(combo)
        b = set(names) - a
        if any((x in a) == (y in a) for x, y in apart) or any((x in a) != (y in a) for x, y in together):
            continue
        gap = abs(sum(skill[n] for n in a) - sum(skill[n] for n in b))
        best = gap if best is None else min(best, gap)
    return best


def test_sample_gap_is_optimal():
    r = split(P, APART, TOGETHER)
    assert r["gap"] == brute_gap(P, APART, TOGETHER) == 1


def test_rules_are_respected():
    r = split(P, APART, TOGETHER)
    assert broken_rules(r, APART, TOGETHER) == []
    assert ("Aiden" in r["team_a"]) != ("Bea" in r["team_a"])


def test_captains_pick_breaks_a_rule_and_is_worse():
    n = top_two_picks(P)
    assert n["gap"] == 5
    assert broken_rules(n, APART, TOGETHER) == ["Gus and Hope are on different teams"]


def test_teams_are_equal_size_and_cover_everyone():
    r = split(P, APART, TOGETHER)
    assert len(r["team_a"]) == len(r["team_b"]) == 5
    assert sorted(r["team_a"] + r["team_b"]) == sorted(p["name"] for p in P)


def test_deterministic():
    assert split(P, APART, TOGETHER) == split(list(reversed(P)), APART, TOGETHER)


def test_random_cases_match_brute_force():
    rng = random.Random(11)
    for _ in range(25):
        n = rng.choice([4, 6, 8])
        players = [{"name": f"p{i}", "skill": rng.randint(1, 10)} for i in range(n)]
        assert split(players)["gap"] == brute_gap(players)


def test_impossible_rules():
    pl = [{"name": "a", "skill": 5}, {"name": "b", "skill": 5}]
    with pytest.raises(TeamError):
        split(pl, [["a", "b"]], [["a", "b"]])


def test_validation():
    with pytest.raises(TeamError):
        split([{"name": "a", "skill": 5}])
    with pytest.raises(TeamError):
        split([{"name": "a", "skill": 50}, {"name": "b", "skill": 5}])
    with pytest.raises(TeamError):
        split(P, [["Aiden", "Nobody"]])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/split", json={"players": P, "keep_apart": APART, "keep_together": TOGETHER}).json()
    assert r["best"]["gap"] == 1 and r["captains_pick"]["gap"] == 5 and r["captains_broken_rules"]
    assert c.get("/").status_code == 200
    assert c.post("/split", json={"players": []}).status_code == 422
