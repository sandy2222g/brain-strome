"""A Bloom filter built from scratch, used as a spell checker's dictionary."""
from __future__ import annotations

import hashlib
import math
import random
import re
import string
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "words.txt"
WORD = re.compile(r"[A-Za-z']+")


class BloomError(ValueError):
    pass


def size_for(n: int, p: float) -> tuple[int, int]:
    """Bits m and hash count k that give false-positive rate p for n items."""
    if n < 1 or not 0 < p < 1:
        raise BloomError("need n >= 1 and 0 < p < 1")
    m = math.ceil(-n * math.log(p) / math.log(2) ** 2)
    k = max(1, round(m / n * math.log(2)))
    return m, k


class Bloom:
    def __init__(self, m: int, k: int) -> None:
        if m < 8 or k < 1:
            raise BloomError("m must be at least 8 and k at least 1")
        self.m, self.k = m, k
        self.bits = bytearray((m + 7) // 8)
        self.count = 0

    def _positions(self, item: str) -> list[int]:
        d = hashlib.blake2b(item.encode(), digest_size=16).digest()
        h1, h2 = int.from_bytes(d[:8], "big"), int.from_bytes(d[8:], "big") | 1
        return [(h1 + i * h2) % self.m for i in range(self.k)]  # double hashing

    def add(self, item: str) -> None:
        for p in self._positions(item):
            self.bits[p >> 3] |= 1 << (p & 7)
        self.count += 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[p >> 3] >> (p & 7) & 1 for p in self._positions(item))

    @property
    def nbytes(self) -> int:
        return len(self.bits)

    def expected_fp(self) -> float:
        """Theory: (1 - e^(-kn/m))^k."""
        return (1 - math.exp(-self.k * self.count / self.m)) ** self.k


def load_words(path: Path = DATA) -> set[str]:
    return {w.strip().lower() for w in path.read_text().split() if w.strip()}


def build(words: set[str], p: float) -> Bloom:
    m, k = size_for(len(words), p)
    b = Bloom(m, k)
    for w in sorted(words):
        b.add(w)
    return b


def measure_fp(b: Bloom, words: set[str], trials: int = 20000, seed: int = 0) -> float:
    """Share of random non-words the filter wrongly says are words."""
    rng = random.Random(seed)
    hits = done = 0
    while done < trials:
        w = "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(5, 9)))
        if w in words:
            continue
        done += 1
        hits += w in b
    return hits / trials


def edits1(w: str) -> set[str]:
    letters = string.ascii_lowercase
    sp = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    out = {a + b[1:] for a, b in sp if b}
    out |= {a + b[1] + b[0] + b[2:] for a, b in sp if len(b) > 1}
    out |= {a + c + b[1:] for a, b in sp if b for c in letters}
    out |= {a + c + b for a, b in sp for c in letters}
    out.discard(w)
    return out


@dataclass(frozen=True)
class Finding:
    word: str
    suggestions: list[str]


def check_text(text: str, b: Bloom, strict: Bloom | None = None) -> list[Finding]:
    """Unknown words get suggestions checked against `strict`, a lower-error filter."""
    pick = strict or b
    out: list[Finding] = []
    seen: set[str] = set()
    for m in WORD.finditer(text):
        w = m.group().lower().strip("'")
        if not w or w in b or w in seen:
            continue
        seen.add(w)
        out.append(Finding(w, sorted(c for c in edits1(w) if c in pick)[:5]))
    return out


@lru_cache(maxsize=8)
def cached(p: float) -> tuple[Bloom, float]:
    words = load_words()
    b = build(words, p)
    return b, measure_fp(b, words)


STRICT_P = 0.0001


def set_bytes(words: set[str]) -> int:
    """Rough memory of keeping the words in a Python set."""
    return sys.getsizeof(words) + sum(sys.getsizeof(w) for w in words)
