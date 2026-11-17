import pytest
from fastapi.testclient import TestClient

from pwcoach.api import app
from pwcoach.core import PasswordError, assess, has_repeats, has_sequence, humanise, passphrase_bits, pool_size

c = TestClient(app)


def test_pool_sizes():
    assert pool_size("abc") == 26 and pool_size("aB") == 52 and pool_size("aB1") == 62 and pool_size("aB1!") == 95


def test_common_passwords_score_zero_even_with_leet_speak():
    for pw in ("password", "letmein", "Qwerty", "dr4g0n"):
        assert assess(pw).score == 0
    assert any("most common" in w for w in assess("password").warnings)


def test_patterns_are_detected():
    assert has_sequence("xxabcdxx") and has_sequence("9876") and has_sequence("QWERT")
    assert not has_sequence("t7#kP2") and has_repeats("aaab") and not has_repeats("abab")


def test_length_beats_cleverness():
    short_complex = assess("T7#kP2!")
    long_words = assess("correct horse battery staple")
    assert long_words.entropy_bits > short_complex.entropy_bits and long_words.score > short_complex.score


def test_word_based_passwords_are_not_overrated():
    famous = assess("Tr0ub4dor&3")  # dictionary word + predictable tweaks (the well-known xkcd example)
    assert famous.score <= 1 and famous.entropy_bits < 35
    assert assess("correct horse battery staple").entropy_bits < 70  # words are cheaper than random letters


def test_entropy_matches_hand_calculation():
    # 8 random lowercase letters: 8 * log2(26) = 37.6 bits
    assert assess("qzvmtbhs").entropy_bits == pytest.approx(37.6, abs=0.1)


def test_crack_time_words():
    assert humanise(0.2) == "instantly" and humanise(90) == "2 minutes" and humanise(86400 * 400).endswith("years")
    assert "universe" in humanise(1e30)


def test_diceware_numbers():
    assert passphrase_bits(4) == pytest.approx(51.7, abs=0.05) and passphrase_bits(6) == pytest.approx(77.5, abs=0.05)


def test_validation():
    with pytest.raises(PasswordError):
        assess("")
    with pytest.raises(PasswordError):
        assess("x" * 129)
    with pytest.raises(PasswordError):
        passphrase_bits(0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.post("/assess", json={"password": "letmein"}).json()
    assert j["score"] == 0 and j["warnings"]
    assert c.post("/assess", json={"password": ""}).status_code == 422
    assert c.get("/passphrase", params={"words": 5}).json()["entropy_bits"] == 64.6
    assert c.get("/passphrase", params={"words": 0}).status_code == 422 and c.get("/").status_code == 200
