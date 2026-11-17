import pytest
from fastapi.testclient import TestClient

from planttree.api import app
from planttree.core import (
    FEATURES,
    TreeError,
    accuracy,
    best_depth,
    best_split,
    evaluate,
    explain,
    fit,
    gini,
    make_data,
    predict,
    rules,
    size,
    splits,
)

c = TestClient(app)


def test_gini():
    assert gini([]) == 0 and gini([1, 1, 1]) == 0 and gini([0, 1]) == 0.5


def test_best_split_finds_the_obvious_cut():
    xs = [[1.0, 9.0], [2.0, 1.0], [3.0, 8.0], [10.0, 2.0], [11.0, 7.0], [12.0, 3.0]]
    f, t, score = best_split(xs, [0, 0, 0, 1, 1, 1], 1)
    assert f == 0 and 3 < t < 10 and score == 0
    assert best_split([[1.0], [1.0], [1.0], [1.0]], [0, 1, 0, 1], 1) is None  # nothing to split on


def test_tree_fits_a_clean_rule_perfectly():
    xs, ys = make_data(300, seed=2, noise=0.0)
    t = fit(xs, ys, 8)
    assert accuracy(t, xs, ys) > 0.95  # the real rule is a blend of features, so axis cuts approximate it


def test_depth_zero_is_the_majority_vote():
    xs, ys = make_data(200, seed=3)
    t = fit(xs, ys, 0)
    assert t.leaf and predict(t, xs[0]) == int(sum(ys) > len(ys) / 2) and size(t) == 1


def test_validation_picks_a_moderate_tree_and_deep_trees_overfit():
    sc = evaluate()
    d = best_depth(sc)
    assert 2 <= d <= 6
    deep = sc[-1]
    assert deep["train"] > sc[d]["train"] and deep["validation"] < sc[d]["validation"]  # memorises, generalises worse


def test_beats_majority_on_held_out_data():
    (tx, ty), (vx, vy), (sx, sy) = splits()
    t = fit(tx, ty, best_depth(evaluate()))
    majority = max(sy.count(0), sy.count(1)) / len(sy)
    assert accuracy(t, sx, sy) > majority + 0.2


def test_explanations_and_rules_match_predictions():
    (tx, ty), _, _ = splits()
    t = fit(tx, ty, 3)
    r = [20.0, 10.0, 8.0, 28.0]
    why = explain(t, r)
    assert why[-1].startswith("-> ") and why[-1].split()[1] == ("water" if predict(t, r) else "skip")
    assert rules(t)[0].startswith("if ") and sum(x.lstrip().startswith("->") for x in rules(t)) == (size(t) + 1) // 2
    assert all(any(f.replace('_', ' ') in line for f in FEATURES) for line in why[:-1])


def test_min_leaf_and_validation():
    xs, ys = make_data(100, seed=4)
    assert size(fit(xs, ys, 8, min_leaf=40)) <= 3
    for bad in [([], [], 3), ([[1.0]], [0, 1], 3), ([[1.0]], [0], -1)]:
        with pytest.raises(TreeError):
            fit(*bad)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    i = c.get("/info").json()
    assert i["test_accuracy"] > i["majority_accuracy"] + 0.2 and i["deep_test_accuracy"] < i["test_accuracy"] + 0.05
    q = {"soil_moisture": 8, "days_since_watering": 9, "sunlight_hours": 9, "temperature_c": 30}
    r = c.get("/predict", params=q).json()
    assert r["answer"] == "water" and len(r["why"]) >= 2 and r["rules"]
    q2 = {**q, "soil_moisture": 55, "days_since_watering": 1}
    assert c.get("/predict", params=q2).json()["answer"] == "skip"
    assert c.get("/predict", params={**q, "depth": 99}).status_code == 422 and c.get("/").status_code == 200
