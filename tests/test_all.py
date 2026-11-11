import pytest
from fastapi.testclient import TestClient

from itemmatch.api import app
from itemmatch.core import MatchError, best_match, build, exact_match, levenshtein, load

RAW = load()
CAT, ITEMS = build(RAW["catalogue"], RAW["items"])
c = TestClient(app)


def test_levenshtein_known_values():
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "abc") == 3
    assert levenshtein("same", "same") == 0
    assert levenshtein("flaw", "lawn") == 2
    assert levenshtein("mlik", "milk") == 1


def test_levenshtein_symmetric():
    for a, b in [("bread", "bred"), ("milk", "mlik"), ("a", "xyz")]:
        assert levenshtein(a, b) == levenshtein(b, a)


def test_triangle_inequality():
    a, b, d = "apples", "aples", "maples"
    assert levenshtein(a, d) <= levenshtein(a, b) + levenshtein(b, d)


def test_typos_resolved():
    assert best_match("aples", CAT)[0] == "apples"
    assert best_match("chiken brest", CAT)[0] == "chicken breast"
    assert best_match("mlik", CAT)[0] == "milk"


def test_nonsense_not_guessed():
    assert best_match("unicorn tears", CAT)[0] is None


def test_exact_baseline_misses_typos():
    assert exact_match("eggs", CAT) == "eggs" and exact_match("aples", CAT) is None


def test_sample_counts():
    fuzzy = sum(best_match(i, CAT)[0] is not None for i in ITEMS)
    exact = sum(exact_match(i, CAT) is not None for i in ITEMS)
    assert (fuzzy, exact) == (11, 1)


def test_normalisation():
    cat, items = build(["Milk"], ["  MILK "])
    assert best_match(items[0], cat) == ("milk", 0)


def test_validation():
    with pytest.raises(MatchError):
        build([], ["a"])
    with pytest.raises(MatchError):
        build(["a", "A"], ["a"])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/match", json=c.get("/sample").json()).json()
    assert r["fuzzy_found"] == 11 and r["exact_found"] == 1
    assert c.get("/").status_code == 200
    assert c.post("/match", json={"catalogue": [], "items": []}).status_code == 422
