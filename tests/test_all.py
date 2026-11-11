import numpy as np
import pytest
from fastapi.testclient import TestClient

from moviepick.api import app, state
from moviepick.core import (
    PickError,
    baselines,
    biases,
    evaluate_groups,
    fit,
    group_pick,
    holdout,
    load,
    rmse,
    to_matrix,
)

D = load()
U, F = len(D["users"]), len(D["films"])
R, M = to_matrix(D["ratings"], U, F)
c = TestClient(app)


def test_to_matrix_roundtrip():
    assert M.sum() == len(D["ratings"]) and R[M].min() >= 1 and R[M].max() <= 5


def test_holdout_is_disjoint_and_keeps_every_user():
    train, test = holdout(M)
    assert not (train & test).any() and (train | test == M).all()
    assert train.any(axis=1).sum() == M.any(axis=1).sum()


def test_biases_shrink_toward_zero_with_few_ratings():
    r = np.array([[5.0, 0.0], [3.0, 3.0]])
    m = np.array([[True, False], [True, True]])
    _, fb = biases(r, m, 3.5, reg=5.0)
    assert abs(fb[0]) < 1.5  # two ratings, heavily shrunk


def test_model_beats_baselines_on_holdout():
    train, test = holdout(M, seed=2)
    model = fit(np.where(train, R, 0.0), train)
    glob, film = baselines(R, train)
    assert rmse(model.predict(), R, test) < rmse(film, R, test) < rmse(glob, R, test) + 0.05
    assert rmse(model.predict(), R, test) < rmse(glob, R, test)


def test_predictions_stay_in_rating_range():
    p = fit(R, M).predict()
    assert p.min() >= 1.0 and p.max() <= 5.0


def test_fit_is_deterministic_and_validates():
    assert np.allclose(fit(R, M).predict(), fit(R, M).predict())
    with pytest.raises(PickError):
        fit(np.zeros((2, 2)), np.zeros((2, 2), dtype=bool))


def test_group_pick_excludes_seen_films_and_sorts():
    pred = fit(R, M).predict()
    picks = group_pick(pred, [0, 1, 2], M, "least_misery", top=5)
    seen = M[[0, 1, 2]].any(axis=0)
    assert all(not seen[p["film"]] for p in picks)
    scores = [p["score"] for p in picks]
    assert scores == sorted(scores, reverse=True)


def test_least_misery_never_below_member_min():
    pred = fit(R, M).predict()
    p = group_pick(pred, [3, 4], M, "least_misery", top=1)[0]
    assert p["score"] == p["min"] <= p["mean"]


def test_group_pick_validation():
    pred = fit(R, M).predict()
    with pytest.raises(PickError):
        group_pick(pred, [], M)
    with pytest.raises(PickError):
        group_pick(pred, [0], M, "random")


def test_group_picks_beat_random_on_true_ratings():
    s = state()
    e = evaluate_groups(s["pred"], s["true"], s["mask"], trials=60)
    assert e["least_misery_min"] > e["random_min"] + 0.4 and e["average_mean"] > e["random_mean"] + 0.4


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    sm = c.get("/sample").json()
    assert len(sm["users"]) == U and len(sm["films"]) == F
    r = c.post("/pick", json={"members": [0, 1, 2], "strategy": "average"}).json()
    assert len(r["picks"]) == 5 and "title" in r["picks"][0]
    m = c.get("/metrics").json()
    assert m["rmse_model"] < m["rmse_global_mean"] and c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/pick", json={"members": [0, 0]}).status_code == 422
    assert c.post("/pick", json={"members": [999]}).status_code == 422
    assert c.post("/pick", json={"members": [1], "strategy": "x"}).status_code == 422
