import pytest
from fastapi.testclient import TestClient

from shrinkmsg.api import app
from shrinkmsg.core import (
    CodingError,
    build_tree,
    code_table,
    decode,
    encode,
    entropy,
    evaluate,
    samples,
    shrink,
)

c = TestClient(app)


def test_known_tree_by_hand():
    table = code_table(build_tree("aaabbc"))  # a:3, b:2, c:1 -> a gets 1 bit, b and c 2 bits
    assert sorted(len(v) for v in table.values()) == [1, 2, 2] and len(table["a"]) == 1
    assert len(encode("aaabbc", table)) == 3 * 1 + 2 * 2 + 1 * 2


def test_prefix_free_and_kraft_equality():
    for s in samples():
        table = code_table(build_tree(s["text"]))
        codes = list(table.values())
        assert not any(a != b and b.startswith(a) for a in codes for b in codes)
        assert sum(2 ** -len(v) for v in codes) == pytest.approx(1.0)  # a full binary tree


def test_exact_round_trip_on_all_samples_and_unicode():
    for text in [s["text"] for s in samples()] + ["héllo wörld ✓ ✓ ✓", "a", "ab", "x" * 50]:
        table = code_table(build_tree(text))
        assert decode(encode(text, table), table) == text


def test_single_symbol_text_still_uses_a_bit_per_char():
    t = code_table(build_tree("aaaa"))
    assert t == {"a": "0"} and encode("aaaa", t) == "0000"


def test_average_length_within_one_bit_of_entropy():
    for s in samples():
        r = shrink(s["text"])
        assert r["entropy"] - 1e-3 <= r["avg_code_len"] < r["entropy"] + 1


def test_size_accounting_by_hand():
    r = shrink("aaabbc")
    assert r["raw_bits"] == 48 and r["payload_bits"] == 9 and r["header_bits"] == 3 * 16
    assert r["total_bits"] == 57 and r["ratio"] == 1.188  # tiny texts expand once the table is counted
    assert entropy("abab") == pytest.approx(1.0)


def test_huffman_beats_raw_on_skewed_text_but_not_always_zlib():
    rows = {r["name"]: r for r in evaluate()}
    assert rows["Skewed DNA"]["ratio"] < rows["Skewed DNA"]["zlib_ratio"]
    assert rows["Repeating pattern"]["zlib_ratio"] < rows["Repeating pattern"]["ratio"]  # zlib exploits repeats
    assert rows["Random letters"]["payload_ratio"] > 0.55  # little redundancy, little gain


def test_validation():
    with pytest.raises(CodingError):
        build_tree("")
    with pytest.raises(CodingError):
        build_tree("x" * 20_001)
    with pytest.raises(CodingError):
        decode("012", {"a": "0", "b": "1"})
    with pytest.raises(CodingError):
        decode("0", {"a": "00", "b": "01", "c": "1"})


def test_api_round_trip():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/shrink", json={"text": "hello hello hello"}).json()
    back = c.post("/expand", json={"table": r["table"], "bits": r["bits"]}).json()
    assert back["text"] == "hello hello hello" and r["payload_bits"] < r["raw_bits"]
    assert c.post("/shrink", json={"text": ""}).status_code == 422
    assert c.post("/expand", json={"table": {"a": "0"}, "bits": "2"}).status_code == 422
    s = c.get("/samples").json()
    assert len(s["samples"]) == 5 and len(s["evaluation"]) == 5 and c.get("/").status_code == 200
