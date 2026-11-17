import pytest
from fastapi.testclient import TestClient

from autocomp.api import app
from autocomp.core import SearchError, Trie, evaluate, load, typo

c = TestClient(app)


def small() -> Trie:
    t = Trie()
    for w, s in [("apple", 5), ("apply", 9), ("app", 1), ("banana", 3), ("sitting", 4)]:
        t.add(w, s)
    return t


def test_prefix_ranks_by_score_then_name():
    assert small().prefix("app", 2) == [("apply", 9), ("apple", 5)]
    assert small().prefix("zzz") == []


def test_prefix_is_case_insensitive():
    assert small().prefix("APP", 1) == [("apply", 9)]


def test_fuzzy_distance_by_hand():
    # "kitten" is 2 edits from the prefix "sittin" of "sitting" (k->s, e->i)
    t = small()
    assert [(w, d) for w, d, _ in t.fuzzy("kitten", 2)] == [("sitting", 2)]
    assert t.fuzzy("kitten", 1) == []


def test_fuzzy_prefers_fewer_edits_then_score():
    t = small()
    got = t.fuzzy("appli", 1)
    assert [w for w, _, _ in got][:2] == ["apply", "apple"] and all(d <= 1 for _, d, _ in got)


def test_suggest_uses_fuzzy_only_when_prefix_is_empty():
    t = small()
    assert t.suggest("app")["mode"] == "prefix"
    r = t.suggest("banan1")
    assert r["mode"] == "fuzzy" and r["results"][0]["name"] == "banana" and r["results"][0]["edits"] == 1


def test_typo_helper():
    assert typo("London", 0) == "lonon" and typo("London", 1) == "lonodn"
    assert typo("London", 2) == "lonzon" and typo("London", 3) == "lonxdon"


def test_beats_prefix_only_baseline_on_typos():
    e = evaluate()
    assert e["queries"] == 612 and e["fuzzy_recall"] == 1.0 and e["baseline_recall"] == 0.008


def test_validation_and_duplicate_add():
    t = small()
    with pytest.raises(SearchError):
        t.suggest("  ")
    with pytest.raises(SearchError):
        t.suggest("a", 0)
    t.add("apple", 50)
    assert t.size == 5 and t.prefix("apple", 1) == [("apple", 50)]


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/suggest", params={"q": "Londno"}).json()
    assert r["mode"] == "fuzzy" and r["results"][0]["name"] == "London"
    assert c.get("/suggest", params={"q": "lon"}).json()["results"][0]["name"] == "London"
    assert c.get("/suggest", params={"q": ""}).status_code == 422
    assert c.get("/evaluation").json()["fuzzy_recall"] == 1.0
    assert load().size == 158 and c.get("/").status_code == 200
