import random
import time

from fastapi.testclient import TestClient

from textdiff.api import app
from textdiff.core import apply, diff_lines, diff_words, distance, lcs_distance, myers, pair_changes, samples, tokens

c = TestClient(app)


def test_identical_and_empty():
    assert distance(myers(list("abc"), list("abc"))) == 0
    assert [o.kind for o in myers([], list("ab"))] == ["add", "add"]
    assert [o.kind for o in myers(list("ab"), [])] == ["del", "del"]
    assert myers([], []) == []


def test_classic_example_from_the_paper():
    a, b = list("ABCABBA"), list("CBABAC")
    ops = myers(a, b)
    assert distance(ops) == 5 and apply(ops) == (a, b)


def test_random_inputs_are_lossless_and_minimal():
    rng = random.Random(7)
    for _ in range(1500):
        a = [rng.choice("abcd") for _ in range(rng.randint(0, 10))]
        b = [rng.choice("abcd") for _ in range(rng.randint(0, 10))]
        ops = myers(a, b)
        assert apply(ops) == (a, b)  # nothing lost, nothing invented
        assert distance(ops) == lcs_distance(a, b)  # as short as the textbook table finds


def test_sample_files():
    s = samples()
    ops = diff_lines(s["a"], s["b"])
    assert apply(ops) == (s["a"].splitlines(), s["b"].splitlines()) and distance(ops) == 9


def test_word_diff_marks_only_the_changed_words():
    ops = diff_words("add one egg", "add two eggs")
    assert [o.text for o in ops if o.kind == "del"] == ["one", "egg"]
    assert [o.text for o in ops if o.kind == "add"] == ["two", "eggs"]
    assert tokens("hi, you") == ["hi", ",", " ", "you"]


def test_rows_pair_changed_lines():
    rows = pair_changes(diff_lines("a\nold line\nz", "a\nnew line\nz\nextra"))
    kinds = [r["kind"] for r in rows]
    assert kinds == ["eq", "chg", "eq", "add"]
    assert rows[1]["old"] == "old line" and rows[1]["new"] == "new line"


def test_fast_when_files_are_similar():
    a = [f"line {i}" for i in range(2000)]
    b = list(a)
    b[10], b[1500] = "changed", "also changed"
    t = time.perf_counter()
    assert distance(myers(a, b)) == 4
    assert time.perf_counter() - t < 1.0  # the O(nm) table would need 4 million cells


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/diff", json={"a": "x\ny", "b": "x\nz\nw"}).json()
    assert r["edits"] == 3 and r["added"] == 2 and r["deleted"] == 1
    assert c.post("/diff", json={"a": "x\n" * 4001, "b": ""}).status_code == 422
    assert "Pancake" in c.get("/sample").json()["a"] and c.get("/").status_code == 200
