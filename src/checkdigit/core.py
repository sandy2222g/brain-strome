"""Check digits: how numbers on cards, books, products and bank accounts catch typing mistakes."""
from __future__ import annotations

import random
import re
from collections.abc import Callable

SCHEMES = ["luhn", "isbn10", "isbn13", "iban"]
IBAN_LENGTHS = {"GB": 22, "DE": 22, "FR": 27, "ES": 24, "IT": 27, "NL": 18}


class CheckError(ValueError):
    pass


def clean(value: str) -> str:
    return re.sub(r"[\s-]", "", value).upper()


def luhn_valid(s: str) -> bool:
    """Double every second digit from the right (subtract 9 if above 9); the total must end in 0."""
    s = clean(s)
    if not s.isdigit() or len(s) < 2:
        return False
    total = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def luhn_complete(body: str) -> str:
    return next(body + str(d) for d in range(10) if luhn_valid(body + str(d)))


def isbn10_valid(s: str) -> bool:
    s = clean(s)
    if not re.fullmatch(r"\d{9}[\dX]", s):
        return False
    return sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(s)) % 11 == 0


def isbn13_valid(s: str) -> bool:
    """Also the EAN-13 product barcode rule: weights 1, 3, 1, 3 ...; total divisible by 10."""
    s = clean(s)
    return bool(re.fullmatch(r"\d{13}", s)) and sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(s)) % 10 == 0


def iban_valid(s: str) -> bool:
    """Move the first four characters to the end, turn letters into numbers (A=10), the result mod 97 must be 1."""
    s = clean(s)
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    if s[:2] in IBAN_LENGTHS and len(s) != IBAN_LENGTHS[s[:2]]:
        return False
    moved = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in moved)) % 97 == 1


VALIDATORS: dict[str, Callable[[str], bool]] = {"luhn": luhn_valid, "isbn10": isbn10_valid, "isbn13": isbn13_valid,
                                                "iban": iban_valid}


def validate(scheme: str, value: str) -> bool:
    if scheme not in VALIDATORS:
        raise CheckError(f"scheme must be one of {', '.join(SCHEMES)}")
    return VALIDATORS[scheme](value)


def random_valid(scheme: str, rng: random.Random) -> str:
    """A random number that passes the check (made up: not anyone's real card, book or account)."""
    if scheme == "luhn":
        return luhn_complete("".join(str(rng.randint(0, 9)) for _ in range(15)))
    if scheme == "isbn13":
        body = "978" + "".join(str(rng.randint(0, 9)) for _ in range(9))
        return next(body + str(d) for d in range(10) if isbn13_valid(body + str(d)))
    if scheme == "isbn10":
        body = "".join(str(rng.randint(0, 9)) for _ in range(9))
        return next(body + c for c in "0123456789X" if isbn10_valid(body + c))
    if scheme == "iban":
        bban = "".join(str(rng.randint(0, 9)) for _ in range(18))
        moved = int("".join(str(int(c, 36)) for c in bban + "GB00"))  # letters become numbers: G=16, B=11
        check = 98 - moved % 97
        return f"GB{check:02d}{bban}"
    raise CheckError(f"scheme must be one of {', '.join(SCHEMES)}")


def corrupt(value: str, kind: str, rng: random.Random) -> str | None:
    """Make one typical typing mistake on the digits; None if the mistake is impossible."""
    chars = list(value)
    idx = [i for i, c in enumerate(chars) if c.isdigit()]
    if kind == "substitution":
        i = rng.choice(idx)
        chars[i] = rng.choice([d for d in "0123456789" if d != chars[i]])
    elif kind == "transposition":
        pairs = [i for i in idx if i + 1 < len(chars) and chars[i + 1].isdigit() and chars[i] != chars[i + 1]]
        if not pairs:
            return None
        i = rng.choice(pairs)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
    elif kind == "twin":
        pairs = [i for i in idx if i + 1 < len(chars) and chars[i + 1].isdigit() and chars[i] == chars[i + 1]]
        if not pairs:
            return None
        i = rng.choice(pairs)
        d = rng.choice([x for x in "0123456789" if x != chars[i]])
        chars[i] = chars[i + 1] = d
    else:
        raise CheckError("kind must be substitution, transposition or twin")
    return "".join(chars)


def experiment(trials: int = 4000, seed: int = 1) -> dict[str, dict[str, float]]:
    """Share of typing mistakes each scheme notices."""
    if not 200 <= trials <= 50000:
        raise CheckError("trials must be 200-50000")
    rng = random.Random(seed)
    out: dict[str, dict[str, float]] = {}
    for s in SCHEMES:
        out[s] = {}
        for kind in ("substitution", "transposition", "twin"):
            caught = total = 0
            attempts = 0
            while total < trials and attempts < trials * 20:
                attempts += 1
                v = random_valid(s, rng)
                bad = corrupt(v, kind, rng)
                if bad is None or bad == v:
                    continue
                total += 1
                caught += not validate(s, bad)
            out[s][kind] = round(caught / max(total, 1), 4)
    return out
