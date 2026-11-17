import pytest
from fastapi.testclient import TestClient

from bloomcheck.api import app
from bloomcheck.core import (
    STRICT_P,
    Bloom,
    BloomError,
    build,
    cached,
    check_text,
    edits1,
    load_words,
    measure_fp,
    set_bytes,
    size_for,
)

c = TestClient(app)
W = load_words()


def test_no_false_negatives():
    for p in (0.2, 0.01, 0.001):
        b = build(W, p)
        assert all(w in b for w in W)  # a Bloom filter never forgets what it holds


def test_sizing_formula():
    m, k = size_for(1000, 0.01)
    assert m == 9586
    assert k == 7
    assert size_for(1000, 0.001)[0] > m > size_for(1000, 0.1)[0]
    for n, p in [(0, 0.1), (10, 0), (10, 1)]:
        with pytest.raises(BloomError):
            size_for(n, p)


def test_measured_false_positive_rate_matches_target():
    for p in (0.05, 0.01):
        b = build(W, p)
        got = measure_fp(b, W, trials=20000)
        assert p / 2 < got < p * 2
        assert abs(b.expected_fp() - p) < p * 0.2


def test_filter_is_far_smaller_than_a_set():
    assert build(W, 0.01).nbytes * 50 < set_bytes(W)


def test_basic_membership_and_validation():
    b = Bloom(256, 3)
    b.add("hello")
    assert "hello" in b and "zzzzzz" not in b
    with pytest.raises(BloomError):
        Bloom(4, 1)


def test_edits1_counts():
    assert len(edits1("cat")) == 181  # 3 deletes + 2 swaps + 75 replaces + 104 inserts - 3 duplicates
    assert {"cot", "ct", "cart", "act"} <= edits1("cat")


def test_spellcheck_finds_typos_and_suggests():
    b, strict = cached(0.01)[0], cached(STRICT_P)[0]
    f = {x.word: x.suggestions for x in check_text("The quik dog went to scool.", b, strict)}
    assert set(f) == {"quik", "scool"} and "quick" in f["quik"] and "school" in f["scool"]
    assert check_text("The dog went to the school", b, strict) == []


def test_ignores_case_and_repeats():
    b = cached(0.01)[0]
    out = check_text("Dog DOG xyzq xyzq", b)
    assert [x.word for x in out] == ["xyzq"]


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/check", params={"text": "the quik dog", "p": 0.01}).json()
    assert [u["word"] for u in r["unknown"]] == ["quik"] and r["filter"]["hashes"] == 7
    assert r["filter"]["bytes"] * 50 < r["filter"]["set_bytes"]
    assert c.get("/check", params={"text": "x", "p": 2}).status_code == 422
    assert c.get("/check", params={"text": "x" * 5001}).status_code == 422
    assert "quik" in c.get("/sample").json()["text"] and c.get("/").status_code == 200
