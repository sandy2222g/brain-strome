import random

import pytest
from fastapi.testclient import TestClient

from checkdigit.api import app
from checkdigit.core import (
    SCHEMES,
    CheckError,
    corrupt,
    experiment,
    iban_valid,
    isbn10_valid,
    isbn13_valid,
    luhn_complete,
    luhn_valid,
    random_valid,
    validate,
)

c = TestClient(app)


def test_luhn_known_numbers():
    assert luhn_valid("79927398713") and luhn_valid("4111 1111 1111 1111") and luhn_valid("4111-1111-1111-1111")
    assert not luhn_valid("79927398710") and not luhn_valid("") and not luhn_valid("12a4") and not luhn_valid("0")
    assert luhn_complete("7992739871") == "79927398713"


def test_isbn_known_numbers():
    assert isbn10_valid("0-306-40615-2") and isbn10_valid("080442957X") and not isbn10_valid("0-306-40615-3")
    assert isbn13_valid("978-0-306-40615-7") and not isbn13_valid("978-0-306-40615-8") and not isbn13_valid("12345")
    assert isbn13_valid("4006381333931")  # an EAN-13 product barcode uses the same rule


def test_iban_known_numbers():
    assert iban_valid("GB82 WEST 1234 5698 7654 32") and iban_valid("DE89 3704 0044 0532 0130 00")
    assert not iban_valid("GB82 WEST 1234 5698 7654 33") and not iban_valid("GB82 WEST 1234 5698 7654")  # wrong length
    assert not iban_valid("XX") and not iban_valid("")


def test_random_numbers_are_valid_and_vary():
    rng = random.Random(0)
    for s in SCHEMES:
        nums = {random_valid(s, rng) for _ in range(50)}
        assert len(nums) > 40 and all(validate(s, n) for n in nums)


def test_corruptions_change_the_number():
    rng = random.Random(1)
    assert corrupt("12345", "substitution", rng) != "12345"
    assert sorted(corrupt("12345", "transposition", rng)) == sorted("12345")  # type: ignore[arg-type]
    assert corrupt("1111", "transposition", rng) is None and corrupt("1234", "twin", rng) is None
    with pytest.raises(CheckError):
        corrupt("123", "typo", rng)


def test_single_digit_errors_are_always_caught():
    r = experiment(2000, seed=3)
    assert all(r[s]["substitution"] == 1.0 for s in SCHEMES)


def test_known_weak_spots_of_each_scheme():
    r = experiment(6000, seed=3)
    assert 0.96 < r["luhn"]["transposition"] < 0.995  # theory 97.8%: misses 09 <-> 90
    assert 0.85 < r["isbn13"]["transposition"] < 0.95  # theory 88.9%: misses digits 5 apart
    assert r["isbn10"]["transposition"] == 1.0  # mod 11 with falling weights catches every swap
    assert r["iban"]["transposition"] > 0.995 and r["iban"]["twin"] > 0.995
    assert r["isbn10"]["twin"] < r["luhn"]["twin"] < 1.0


def test_luhn_blind_spot_for_09_swaps():
    base = luhn_complete("12090")
    swapped = base[:2] + "90" + base[4:]  # swap the adjacent 0 and 9
    assert base[2:4] == "09" and luhn_valid(base) and luhn_valid(swapped)
    ordinary = luhn_complete("12340")
    assert not luhn_valid(ordinary[:2] + "43" + ordinary[4:])  # any other swap is noticed


def test_validation_and_api():
    with pytest.raises(CheckError):
        validate("nope", "1")
    with pytest.raises(CheckError):
        experiment(5)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/validate", params={"scheme": "luhn", "value": "4111 1111 1111 1111"}).json()["valid"] is True
    assert c.get("/validate", params={"scheme": "luhn", "value": "4111 1111 1111 1112"}).json()["valid"] is False
    assert c.get("/validate", params={"scheme": "x", "value": "1"}).status_code == 422
    assert c.get("/validate", params={"scheme": "luhn", "value": "1" * 80}).status_code == 422
    assert c.get("/experiment", params={"trials": 1000}).json()["rates"]["isbn10"]["transposition"] == 1.0
    assert set(c.get("/examples").json()["examples"]) == set(SCHEMES) and c.get("/").status_code == 200
