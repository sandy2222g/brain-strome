import math

import pytest
from fastapi.testclient import TestClient

from outfitpick.api import app
from outfitpick.core import (
    CLASSES,
    OutfitError,
    accuracy,
    evaluate,
    load,
    recommend,
    scaler,
    softmax,
    split,
    train,
)

c = TestClient(app)
MODEL = train(split(load())[0])


def test_softmax_sums_to_one_and_is_stable():
    p = softmax([1.0, 2.0, 3.0])
    assert sum(p) == pytest.approx(1.0) and p[2] > p[1] > p[0]
    big = softmax([1000.0, 1000.0])
    assert big == pytest.approx([0.5, 0.5])


def test_softmax_by_hand():
    assert softmax([0.0, math.log(3)]) == pytest.approx([0.25, 0.75])


def test_scaler_by_hand():
    mean, sd = scaler([[1.0, 0.0, 5.0], [3.0, 0.0, 5.0]])
    assert mean == [2.0, 0.0, 5.0] and sd == [1.0, 1.0, 1.0]  # zero variance falls back to 1


def test_split_holds_out_every_fourth():
    tr, te = split(load())
    assert len(tr) == 180 and len(te) == 60


def test_beats_majority_baseline():
    e = evaluate()
    assert e["accuracy"] == 0.85 and e["baseline"] == 0.333
    assert accuracy(MODEL, split(load())[1]) > 0.8


def test_sensible_recommendations():
    assert recommend(MODEL, 2, 10, 0)["outfit"] == "coat"
    assert recommend(MODEL, 28, 3, 0)["outfit"] == "light"
    assert recommend(MODEL, 15, 5, 8)["outfit"] == "raincoat"
    r = recommend(MODEL, 15, 10, 0)
    assert sum(r["probabilities"].values()) == pytest.approx(1.0, abs=0.01)
    assert set(r["probabilities"]) == set(CLASSES)


def test_validation():
    with pytest.raises(OutfitError):
        recommend(MODEL, 100, 0, 0)
    with pytest.raises(OutfitError):
        recommend(MODEL, 10, -1, 0)
    with pytest.raises(OutfitError):
        train(load()[:3])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/recommend", json={"temp_c": 4, "wind_kph": 15}).json()
    assert r["outfit"] == "coat" and 0 < r["confidence"] <= 1
    assert c.post("/recommend", json={"temp_c": 99}).status_code == 422
    assert c.get("/evaluation").json()["accuracy"] == 0.85
    assert c.get("/").status_code == 200
