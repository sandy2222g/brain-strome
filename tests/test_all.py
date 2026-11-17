import math

import pytest
from fastapi.testclient import TestClient

from binsort.api import app
from binsort.core import NaiveBayes, SortError, evaluate, load_rows, majority_accuracy, split, tokens, trained

c = TestClient(app)


def test_tokens():
    assert tokens("Plastic Bottle, 2L!") == ["plastic", "bottle", "l"]


def test_naive_bayes_by_hand():
    rows = [("red apple", "a"), ("red car", "b")]
    m = NaiveBayes().fit(rows)
    # vocab {red, apple, car}=3, each class has 2 tokens; P(apple|a)=(1+1)/(2+3)=.4, P(apple|b)=(0+1)/(2+3)=.2
    p = m.proba("apple")
    assert p["a"] == pytest.approx(0.4 / (0.4 + 0.2))
    assert math.isclose(sum(p.values()), 1.0)
    assert m.predict("car") == "b"


def test_unknown_words_fall_back_to_the_prior():
    m = NaiveBayes().fit([("x", "a"), ("y", "a"), ("z", "b")])
    assert m.predict("neverseen") == "a"


def test_split_is_stratified_and_disjoint():
    rows = load_rows()
    train, test = split(rows)
    assert len(train) + len(test) == len(rows)
    assert {y for _, y in test} == {y for _, y in rows}
    assert not set(train) & set(test)


def test_beats_majority_baseline_on_held_out_items():
    r = evaluate()
    assert r["majority"] == 0.25
    assert r["naive_bayes"] >= 0.6 and r["naive_bayes"] > r["majority"] + 0.3
    train, test = split(load_rows())
    assert majority_accuracy(train, test) == 0.25


def test_obvious_items():
    m = trained()
    assert m.predict("glass bottle") == "recycling"
    assert m.predict("banana skin") == "compost"
    assert m.predict("old phone charger") == "e-waste"
    assert m.predict("plastic bag") == "landfill"


def test_validation():
    with pytest.raises(SortError):
        NaiveBayes().fit([])
    with pytest.raises(SortError):
        trained().proba("!!!")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/classify", json={"item": "banana skin"}).json()
    assert r["bin"] == "compost" and abs(sum(r["probabilities"].values()) - 1) < 0.01
    assert c.get("/metrics").json()["majority"] == 0.25
    assert c.post("/classify", json={"item": "???"}).status_code == 422
    assert c.get("/").status_code == 200
