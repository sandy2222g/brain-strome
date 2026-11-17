import pytest
from fastapi.testclient import TestClient

from langguess.api import app
from langguess.core import LangError, Model, accuracy, evaluate, full_model, grams, load, split

c = TestClient(app)


def test_grams_by_hand():
    assert grams("ab", 2) == [" a", "ab", "b "]
    assert grams("  A  B ", 1) == [" ", "a", " ", "b", " "]  # case folded, whitespace collapsed
    assert grams("x", 3) == [" x "]


def test_tiny_model_is_decided_by_letters():
    m = Model({"A": ["aaaa aaa"], "B": ["bbbb bbb"]}, 1)
    assert m.guess("aa")["language"] == "A" and m.guess("bbb")["language"] == "B"
    s = m.scores("ab")
    assert set(s) == {"A", "B"} and all(v < 0 for v in s.values())  # log probabilities


def test_probabilities_sum_to_one_and_are_sorted():
    r = full_model().guess("Dove si trova la stazione")
    ps = [x["p"] for x in r["ranking"]]
    assert sum(ps) == pytest.approx(1.0, abs=0.01) and ps == sorted(ps, reverse=True)
    assert r["language"] == r["ranking"][0]["language"] == "Italian"


def test_split_is_fourteen_train_six_test_per_language():
    train, test = split(load())
    assert all(len(v) == 14 for v in train.values()) and len(test) == 30
    assert not {s for v in train.values() for s in v} & {s for _, s in test}  # no leakage


def test_trigrams_beat_single_letters_especially_on_short_text():
    e = evaluate()
    assert e["trigram"] == 1.0 and e["unigram"] == 0.967
    assert e["trigram_short"] == 0.933 and e["unigram_short"] == 0.7
    assert e["trigram_short"] > e["unigram_short"] > e["chance"]


def test_accuracy_helper_and_held_out_use():
    train, test = split(load())
    assert accuracy(Model(train, 3), test) == 1.0


def test_unseen_language_gets_a_best_guess_not_a_crash():
    r = full_model().guess("Это русское предложение")
    assert r["language"] in {"English", "French", "German", "Italian", "Spanish"}


def test_validation():
    with pytest.raises(LangError):
        Model({"A": ["a"]})
    with pytest.raises(LangError):
        full_model().guess("   ")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert c.post("/guess", json={"text": "Ich möchte bitte eine Tasse Tee"}).json()["language"] == "German"
    assert c.post("/guess", json={"text": ""}).status_code == 422
    assert len(c.get("/examples").json()["examples"]) == 5
    assert c.get("/evaluation").json()["trigram"] == 1.0 and c.get("/").status_code == 200
