import itertools
import json
import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from washrota.api import app
from washrota.core import RotaError, assign, build_cost, first_come, hungarian, summary, total_cost

S = json.loads(Path("data/sample_block.json").read_text())
c = TestClient(app)


def brute(cost):
    n = len(cost)
    return min(sum(cost[i][p[i]] for i in range(n)) for p in itertools.permutations(range(n)))


def test_hungarian_matches_brute_force():
    rng = random.Random(5)
    for _ in range(80):
        n = rng.randint(1, 6)
        m = [[float(rng.randint(0, 12)) for _ in range(n)] for _ in range(n)]
        cols = hungarian(m)
        assert sorted(cols) == list(range(n))
        assert sum(m[i][cols[i]] for i in range(n)) == brute(m)


def test_hungarian_rejects_bad_matrix():
    with pytest.raises(RotaError):
        hungarian([])
    with pytest.raises(RotaError):
        hungarian([[1, 2]])


def test_assignment_is_one_slot_each():
    plan = assign(S["slots"], S["residents"])
    assert len(set(plan.values())) == len(plan) == len(S["residents"])


def test_never_worse_than_first_come():
    best = total_cost(S["residents"], assign(S["slots"], S["residents"]))
    naive = total_cost(S["residents"], first_come(S["slots"], S["residents"]))
    assert best <= naive


def test_beats_first_come_on_contested_slot():
    slots = ["a", "b"]
    prefs = {"x": ["a", "b"], "y": ["a"]}
    assert summary(prefs, assign(slots, prefs))["no_choice"] == 0
    assert summary(prefs, first_come(slots, prefs))["no_choice"] == 1


def test_sample_is_oversubscribed_and_optimum_beats_first_come():
    best = summary(S["residents"], assign(S["slots"], S["residents"]))
    naive = summary(S["residents"], first_come(S["slots"], S["residents"]))
    assert best["no_choice"] == 1  # four flats want Sat 09:00 or its neighbours; someone must lose
    assert best["total_cost"] == 14 and naive["total_cost"] == 23


def test_spare_slots_are_fine_and_overbooking_is_not():
    assert len(assign(["a", "b", "c"], {"x": ["a"]})) == 1
    with pytest.raises(RotaError):
        assign(["a"], {"x": ["a"], "y": ["a"]})


def test_validation():
    with pytest.raises(RotaError):
        build_cost(["a", "a"], {"x": ["a"]})
    with pytest.raises(RotaError):
        build_cost(["a", "b"], {"x": ["z"]})
    with pytest.raises(RotaError):
        build_cost(["a", "b"], {"x": ["a", "a"]})


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/assign", json=c.get("/sample").json()).json()
    assert r["summary"]["total_cost"] <= r["first_come_summary"]["total_cost"]
    assert c.get("/").status_code == 200


def test_api_errors():
    assert c.post("/assign", json={"slots": ["a"], "residents": {"x": ["a"], "y": ["a"]}}).status_code == 422
