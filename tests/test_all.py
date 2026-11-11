import itertools
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from santadraw.api import app
from santadraw.core import DrawError, allowed, count_draws, draw, is_valid

S = json.loads(Path("data/sample_group.json").read_text())
N, EX, LAST = S["names"], [tuple(p) for p in S["exclusions"]], S["last_year"]
c = TestClient(app)


def test_every_draw_is_valid():
    for seed in range(200):
        assert is_valid(draw(N, EX, LAST, seed), N, EX, LAST)


def test_no_self_gifts_and_everyone_receives_once():
    r = draw(N, seed=1)
    assert all(g != x for g, x in r.items()) and sorted(r.values()) == sorted(N)


def test_seed_is_deterministic_and_seeds_vary():
    assert draw(N, EX, LAST, 5) == draw(N, EX, LAST, 5)
    assert len({tuple(sorted(draw(N, EX, LAST, s).items())) for s in range(30)}) > 5


def test_all_valid_draws_reachable_small_group():
    names = ["a", "b", "c", "d"]
    seen = {tuple(sorted(draw(names, seed=s).items())) for s in range(400)}
    assert len(seen) == count_draws(names) == 9


def test_count_matches_brute_force():
    names, ex = ["a", "b", "c", "d", "e"], [("a", "b"), ("c", "d")]
    bad = {frozenset(p) for p in ex}
    brute = sum(
        1
        for p in itertools.permutations(names)
        if all(g != r and frozenset((g, r)) not in bad for g, r in zip(names, p, strict=True))
    )
    assert count_draws(names, ex) == brute


def test_last_year_excluded():
    assert LAST["Asha"] not in allowed(N, EX, LAST)["Asha"]


def test_infeasible_is_detected():
    with pytest.raises(DrawError):
        draw(["a", "b", "c"], [("a", "b"), ("a", "c")])


def test_input_validation():
    for names, ex in (
        (["a", "b"], []),
        (["a", "a", "b"], []),
        (["a", "b", "c"], [("a", "z")]),
        (["a", "b", "c"], [("a", "a")]),
    ):
        with pytest.raises(DrawError):
            draw(names, ex)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/draw", json={**c.get("/sample").json(), "seed": 3}).json()
    assert is_valid(r["assignments"], N, EX, LAST) and r["possible_draws"] > 0
    assert c.get("/").status_code == 200


def test_api_infeasible_422():
    body = {"names": ["a", "b", "c"], "exclusions": [["a", "b"], ["a", "c"]]}
    assert c.post("/draw", json=body).status_code == 422
