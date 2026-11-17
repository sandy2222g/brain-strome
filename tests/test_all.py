import pytest
from fastapi.testclient import TestClient

from wordhive.api import app
from wordhive.core import HiveError, check_hive, is_pangram, load, rank, score, solve

D = load()
c = TestClient(app)
LET = frozenset(D["letters"])


def test_scoring_rules():
    assert score("deal", LET) == 1
    assert score("angel", LET) == 5
    assert score("dealing", LET) == 7 + 7  # 7 letters plus the pangram bonus


def test_pangram_detection():
    assert is_pangram("aligned", LET) and not is_pangram("angel", LET)


def test_sample_counts():
    r = solve(D["words"], D["letters"], D["center"])
    assert r["count"] == 51 and r["total_points"] == 195
    assert r["pangrams"] == ["aligned", "dealing", "leading"]


def test_every_word_has_centre_and_only_hive_letters():
    for w in solve(D["words"], D["letters"], D["center"])["words"]:
        assert "e" in w["word"] and set(w["word"]) <= LET and len(w["word"]) >= 4


def test_centre_letter_changes_the_answer():
    with_e = solve(D["words"], D["letters"], "e")["count"]
    with_g = solve(D["words"], D["letters"], "g")["count"]
    assert with_e != with_g


def test_short_words_and_duplicates_ignored():
    r = solve(["dig", "deal", "DEAL", "deal"], "dealing", "e")
    assert [w["word"] for w in r["words"]] == ["deal"]


def test_sorted_best_first():
    pts = [w["points"] for w in solve(D["words"], D["letters"], "e")["words"]]
    assert pts == sorted(pts, reverse=True)


def test_rank_labels():
    assert rank(0, 100) == "Beginner" and rank(10, 100) == "Nice" and rank(25, 100) == "Good"
    assert rank(50, 100) == "Great" and rank(70, 100) == "Genius" and rank(0, 0) == "Beginner"


def test_validation():
    with pytest.raises(HiveError):
        check_hive("abc", "a")
    with pytest.raises(HiveError):
        check_hive("aabcdef", "a")
    with pytest.raises(HiveError):
        check_hive("abcdefg", "z")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/solve", json={"letters": "dealing", "center": "e"}).json()
    assert r["count"] == 51 and r["ranks"]["half"] in {"Great", "Good"}
    assert c.get("/").status_code == 200
    assert c.post("/solve", json={"letters": "dealing", "center": "z"}).status_code == 422
