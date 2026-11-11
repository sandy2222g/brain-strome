import random

import pytest
from fastapi.testclient import TestClient

from mealmix.api import app
from mealmix.core import Food, MixError, Targets, best_mix, build, cheapest_per_kcal, load, meets, totals

FOODS, TARGETS, CAP = load()
BEST = best_mix(FOODS, TARGETS, CAP)
BASE = cheapest_per_kcal(FOODS, TARGETS, CAP)
c = TestClient(app)


def test_totals_by_hand():
    foods = [Food("a", 1.5, 100, 10), Food("b", 0.25, 50, 0)]
    assert totals(foods, [2, 4]) == (4.0, 400, 20)


def test_best_mix_meets_every_target_and_the_serving_cap():
    assert meets(FOODS, TARGETS, BEST) and max(BEST) <= CAP


def test_baseline_misses_the_protein_target_on_the_sample():
    assert not meets(FOODS, TARGETS, BASE)
    assert totals(FOODS, BASE)[2] < TARGETS.protein_min


def test_sample_numbers():
    assert totals(FOODS, BEST) == (3.9, 2105, 110)
    assert totals(FOODS, BASE) == (3.55, 2110, 90)


def test_no_random_feasible_mix_is_cheaper_than_the_best():
    rng = random.Random(0)
    best_cost = totals(FOODS, BEST)[0]
    feasible = 0
    for _ in range(20000):
        mix = [rng.randint(0, CAP) for _ in FOODS]
        if meets(FOODS, TARGETS, mix):
            feasible += 1
            assert totals(FOODS, mix)[0] >= best_cost - 1e-9
    assert feasible > 0


def test_tighter_protein_target_never_costs_less():
    tight = Targets(TARGETS.kcal_min, TARGETS.kcal_max, TARGETS.protein_min + 20)
    assert totals(FOODS, best_mix(FOODS, tight, CAP))[0] >= totals(FOODS, BEST)[0]


def test_infeasible_targets_raise():
    with pytest.raises(MixError):
        best_mix(FOODS, Targets(2000, 2300, 900), CAP)


def test_validation():
    with pytest.raises(MixError):
        build([], TARGETS, 4)
    with pytest.raises(MixError):
        build(FOODS, Targets(2000, 1000, 10), 4)
    with pytest.raises(MixError):
        build([Food("a", 1, 100, 1), Food("a", 1, 100, 1)], TARGETS, 4)
    with pytest.raises(MixError):
        build(FOODS, TARGETS, 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/mix", json=c.get("/sample").json()).json()
    assert r["best"]["meets_targets"] and not r["baseline"]["meets_targets"]
    assert r["best"]["cost"] == 3.9 and r["baseline"]["protein"] == 90
    assert c.get("/").status_code == 200


def test_api_validation():
    body = c.get("/sample").json()
    body["targets"]["protein_min"] = 900
    assert c.post("/mix", json=body).status_code == 422
