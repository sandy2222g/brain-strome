import random

import pytest
from fastapi.testclient import TestClient

from huffsqueeze.api import SAMPLES, app
from huffsqueeze.core import HuffmanError, analyse, build_codes, decode, encode, entropy_bits

c = TestClient(app)


def test_known_textbook_example():
    # classic frequencies a:45 b:13 c:12 d:16 e:9 f:5 -> total cost 224 bits per 100 symbols
    text = "a" * 45 + "b" * 13 + "c" * 12 + "d" * 16 + "e" * 9 + "f" * 5
    codes = build_codes(text)
    assert len(encode(text, codes)) == 224
    assert len(codes["a"]) == 1 and len(codes["e"]) == len(codes["f"]) == 4


def test_codes_are_prefix_free():
    codes = build_codes("the quick brown fox jumps over the lazy dog")
    for a in codes.values():
        for b in codes.values():
            assert a == b or not b.startswith(a)


def test_round_trip_on_random_text():
    rng = random.Random(1)
    for _ in range(100):
        t = "".join(rng.choice("abcdé \n") for _ in range(rng.randint(1, 200)))
        codes = build_codes(t)
        assert decode(encode(t, codes), codes) == t


def test_never_beats_entropy_and_is_within_one_bit():
    for t in SAMPLES.values():
        a = analyse(t)
        h = entropy_bits(t)
        assert h <= a["bits_per_char"] < h + 1  # Huffman's guarantee


def test_single_symbol_and_errors():
    assert build_codes("aaaa") == {"a": "0"}
    with pytest.raises(HuffmanError):
        build_codes("")
    with pytest.raises(HuffmanError):
        decode("01", {"a": "000", "b": "1"})


def test_zlib_wins_on_repetition_huffman_cannot():
    a = analyse(SAMPLES["repetitive"])
    assert a["zlib_bytes"] < a["huffman_bytes"] / 2  # Huffman ignores repeated patterns
    assert a["bits_per_char"] == 1.0


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.post("/analyse", json={"text": "hello world"}).json()
    assert j["chars"] == 11 and j["bits_per_char"] >= j["entropy"]
    assert c.post("/analyse", json={"text": ""}).status_code == 422
    assert len(c.get("/samples").json()["samples"]) == 3 and c.get("/").status_code == 200
