import pytest
from fastapi.testclient import TestClient

from typecoach.api import app
from typecoach.core import (
    TypingError,
    align,
    analyse,
    drill,
    evaluate,
    load_sessions,
    naive_errors,
    weak_keys,
)

c = TestClient(app)


def kinds(a: str, b: str) -> list[str]:
    return [o[0] for o in align(a, b)]


def test_alignment_kinds():
    assert align("cat", "cut") == [("match", "c", "c"), ("sub", "a", "u"), ("match", "t", "t")]
    assert kinds("cat", "ct").count("miss") == 1 and kinds("cat", "ct").count("match") == 2
    assert kinds("cat", "caat").count("extra") == 1
    assert kinds("same", "same") == ["match"] * 4


def test_naive_comparison_over_counts_after_a_dropped_letter():
    assert naive_errors("abcdef", "bcdef") == 6
    assert sum(k != "match" for k in kinds("abcdef", "bcdef")) == 1


def test_wpm_and_accuracy_by_hand():
    clean = analyse("hello world", "hello world", 6)
    assert clean["gross_wpm"] == 22.0 and clean["net_wpm"] == 22.0 and clean["accuracy"] == 1.0
    one = analyse("hello world", "hello worlf", 6)
    assert one["errors"] == 1 and one["net_wpm"] == 12.0 and one["accuracy"] == 0.909
    assert one["confusions"] == [["d", "f", 1]]


def test_net_wpm_never_negative():
    assert analyse("abcdefgh", "zzzzzzzz", 60)["net_wpm"] == 0.0


def test_seen_and_missed_counts_ignore_spaces():
    r = analyse("a b", "x b", 5)
    assert r["seen"] == {"a": 1, "b": 1} and r["missed"] == {"a": 1, "b": 0}


def test_weak_keys_rank_by_rate_and_need_enough_attempts():
    rs = [{"seen": {"r": 10, "q": 2, "e": 20}, "missed": {"r": 3, "q": 2, "e": 2}}]
    got = weak_keys(rs)
    assert [g["key"] for g in got] == ["r", "e"]  # q has only 2 attempts
    assert got[0]["miss_rate"] == 0.3


def test_drill_prefers_words_dense_in_weak_letters():
    assert drill(["r"], ["tree", "red", "sun", "error"]) == ["error", "red", "tree"]
    with pytest.raises(TypingError):
        drill([], ["a"])


def test_alignment_matches_ground_truth_but_naive_does_not():
    e = evaluate()
    assert e["aligned_gap"] == 0.0 and e["naive_gap"] == 36.6
    assert [s["true_errors"] for s in e["sessions"]] == [9, 3, 4, 7, 6]
    assert len(load_sessions()) == 5


def test_validation():
    with pytest.raises(TypingError):
        analyse("", "x", 5)
    with pytest.raises(TypingError):
        analyse("x", "x", 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/analyse", json={"target": "hello world", "typed": "hello worlf", "seconds": 6}).json()
    assert r["net_wpm"] == 12.0
    assert c.post("/analyse", json={"target": "a", "typed": "", "seconds": 6}).status_code == 422
    co = c.get("/coach").json()
    assert co["weak_keys"][0]["key"] == "r" and len(co["drill"]) == 8 and co["net_wpm"][-1] == 30.8
    assert c.get("/evaluation").json()["aligned_gap"] == 0.0
    assert len(c.get("/sample").json()["sessions"]) == 5 and c.get("/").status_code == 200
