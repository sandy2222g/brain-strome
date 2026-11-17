"""Password strength estimation: pool-size entropy, pattern penalties and a plain-English crack time."""
from __future__ import annotations

import math
import string
from dataclasses import dataclass

# A tiny, generic list of well-known weak choices (common knowledge, not a leaked dataset).
COMMON = {
    "password", "123456", "12345678", "qwerty", "abc123", "letmein", "welcome", "monkey", "dragon", "football",
    "iloveyou", "admin", "login", "master", "sunshine", "princess", "shadow", "superman", "baseball", "trustno1",
}
LEET = str.maketrans("4@310$5!7", "aaeiossit"[:9])
# Small stand-in for a dictionary: real crackers use far bigger lists, so estimates here err on the generous side.
WORDS = {
    "correct", "horse", "battery", "staple", "troubador", "dragon", "monkey", "sunshine", "summer", "winter", "purple",
    "orange", "banana", "coffee", "guitar", "soccer", "hockey", "cookie", "flower", "garden", "pepper", "silver",
    "golden", "tiger", "rabbit", "planet", "rocket", "castle", "forest", "river", "ocean", "mountain", "pizza",
    "chocolate", "butter", "cheese", "table", "window", "yellow", "green", "blue", "red", "love", "hello", "magic",
    "puppy", "kitten", "bridge", "pass", "word", "my", "the", "is", "of", "and", "cat", "dog", "sun", "moon", "star",
}
WORD_BITS = 11.0  # about log2(2048): a generous common-word vocabulary
KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890"]
GUESSES_PER_SECOND = 1e10  # an offline attacker with a fast GPU rig against a fast hash


class PasswordError(ValueError):
    """Raised for invalid input."""


@dataclass(frozen=True)
class Report:
    score: int  # 0 (terrible) to 4 (strong)
    entropy_bits: float
    crack_time: str
    warnings: list[str]


def pool_size(pw: str) -> int:
    pool = 0
    if any(c in string.ascii_lowercase for c in pw):
        pool += 26
    if any(c in string.ascii_uppercase for c in pw):
        pool += 26
    if any(c in string.digits for c in pw):
        pool += 10
    if any(not c.isalnum() for c in pw):
        pool += 33
    return pool


def word_aware_bits(pw: str) -> float | None:
    """If dictionary words (with leet-speak and capitals) explain part of the password, cost them as words."""
    plain = pw.lower().translate(LEET)
    subs = sum(1 for a, b in zip(pw.lower(), plain, strict=True) if a != b)
    i, words, rest = 0, 0, 0
    while i < len(plain):
        match = next((w for w in sorted(WORDS, key=len, reverse=True) if len(w) >= 3 and plain.startswith(w, i)), None)
        if match:
            words += 1
            i += len(match)
        else:
            rest += 1
            i += 1
    if words == 0:
        return None
    caps = 1.0 if any(c.isupper() for c in pw) else 0.0
    return words * WORD_BITS + rest * math.log2(max(pool_size(pw), 2)) + subs * 2.0 + caps


def has_sequence(pw: str, n: int = 4) -> bool:
    """True if the password contains n or more characters in a row that walk the alphabet, digits or a keyboard row."""
    low = pw.lower()
    for seq in [string.ascii_lowercase, string.digits, *KEYBOARD_ROWS]:
        for s in (seq, seq[::-1]):
            for i in range(len(s) - n + 1):
                if s[i:i + n] in low:
                    return True
    return False


def has_repeats(pw: str, n: int = 3) -> bool:
    return any(len(set(pw[i:i + n])) == 1 for i in range(len(pw) - n + 1))


def humanise(seconds: float) -> str:
    if seconds < 1:
        return "instantly"
    steps = (("seconds", 60), ("minutes", 60), ("hours", 24), ("days", 365), ("years", 100), ("centuries", 1e9))
    for unit, size in steps:
        if seconds < size:
            return f"{seconds:.0f} {unit}"
        seconds /= size
    return "longer than the age of the universe"


def assess(pw: str) -> Report:
    if not pw:
        raise PasswordError("password must not be empty")
    if len(pw) > 128:
        raise PasswordError("password too long (max 128 characters)")
    warnings: list[str] = []
    low = pw.lower()
    plain = low.translate(LEET)
    bits = len(pw) * math.log2(max(pool_size(pw), 2))
    wb = word_aware_bits(pw)
    if wb is not None and wb < bits:
        bits = wb
        warnings.append("Built from dictionary words, which attackers combine and swap letters in first.")
    if low in COMMON or plain in COMMON:
        warnings.append("This is one of the most common passwords; attackers try it first.")
        bits = min(bits, 10.0)
    if has_sequence(pw):
        warnings.append("Contains a keyboard or alphabet run such as 'abcd' or 'qwer'.")
        bits *= 0.6
    if has_repeats(pw):
        warnings.append("Repeats the same character three or more times.")
        bits *= 0.7
    if len(pw) < 12:
        warnings.append("Shorter than 12 characters; length matters more than symbols.")
    if pw.isalpha() or pw.isdigit():
        warnings.append("Uses only one kind of character.")
    seconds = (2 ** bits) / 2 / GUESSES_PER_SECOND  # on average half the space is searched
    score = 0 if bits < 28 else 1 if bits < 40 else 2 if bits < 60 else 3 if bits < 80 else 4
    return Report(score, round(bits, 1), humanise(seconds), warnings)


def passphrase_bits(words: int, dictionary: int = 7776) -> float:
    """Entropy of randomly chosen dictionary words (diceware uses a 7,776-word list)."""
    if words < 1:
        raise PasswordError("need at least one word")
    return round(words * math.log2(dictionary), 1)
