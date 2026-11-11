import pytest
from fastapi.testclient import TestClient

from spamshield.api import app
from spamshield.core import DATA, NaiveBayes, SpamError, evaluate, features, load_csv, split

ROWS = load_csv(DATA / "messages.csv")
HARD = load_csv(DATA / "hard_cases.csv")
TRAIN, TEST = split(ROWS)
M = NaiveBayes().fit(TRAIN)
c = TestClient(app)


def test_features_include_bigrams_and_shape_flags():
    f = features("WINNER! Claim at prize.example now 123")
    assert "claim" in f and "claim_at" in f and "__url__" in f and "__digit__" in f and "__caps__" in f


def test_fit_validates():
    with pytest.raises(SpamError):
        NaiveBayes().fit([])
    with pytest.raises(SpamError):
        NaiveBayes().fit([("spam", "x"), ("maybe", "y")])
    with pytest.raises(SpamError):
        NaiveBayes().fit([("ham", "x"), ("ham", "y")])


def test_obvious_cases():
    assert M.predict("WINNER! claim your free prize at win.example") == "spam"
    assert M.predict("can you pick up milk on the way home") == "ham"


def test_probability_in_range_and_consistent_with_label():
    for _, text in TEST[:40]:
        p = M.prob_spam(text)
        assert 0 <= p <= 1 and (p > 0.5) == (M.predict(text) == "spam")


def test_template_test_set_is_nearly_perfect_but_not_the_real_bar():
    e = evaluate(M, TEST)
    assert e["accuracy"] >= 0.98 and e["n"] == len(TEST)


def test_hard_cases_are_much_harder_and_threshold_trades_recall_for_precision():
    strict, loose = evaluate(M, HARD, 2), evaluate(M, HARD, -4)
    assert evaluate(M, HARD)["accuracy"] < evaluate(M, TEST)["accuracy"]
    assert loose["recall"] > strict["recall"] and loose["false_positives"] >= strict["false_positives"]


def test_hard_cases_beat_always_ham_baseline_at_a_loose_threshold():
    base = sum(1 for lab, _ in HARD if lab == "ham") / len(HARD)
    assert evaluate(M, HARD, -2)["accuracy"] > base


def test_explanations_name_the_spammy_features():
    reasons = dict(M.explain("claim your free prize at win.example"))
    assert any(w > 0 for w in reasons.values()) and "__url__" in reasons


def test_unseen_words_are_ignored_not_crash():
    assert M.predict("zzzzqqq xyzzy plugh") in {"spam", "ham"}


def test_evaluate_counts_add_up():
    e = evaluate(M, HARD, 0)
    assert e["false_positives"] + e["false_negatives"] <= e["n"]


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/predict", json={"text": "WINNER! claim your free prize at win.example"}).json()
    assert r["label"] == "spam" and r["reasons"] and 0.5 < r["spam_probability"] <= 1
    assert len(c.get("/examples").json()) == len(HARD)
    m = c.get("/metrics").json()
    assert m["template_test"]["accuracy"] >= 0.98 and len(m["hard_cases"]) == 4
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/predict", json={"text": ""}).status_code == 422
    assert c.post("/predict", json={"text": "hi", "threshold": 99}).status_code == 422
