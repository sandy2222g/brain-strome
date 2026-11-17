"""A character n-gram language model that invents place names."""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "villages.txt"
START, END = "^", "$"


class MakerError(ValueError):
    pass


def load_names(path: Path = DATA) -> list[str]:
    return [n.strip().lower() for n in path.read_text().splitlines() if n.strip()]


def split(names: list[str], every: int = 5) -> tuple[list[str], list[str]]:
    """Deterministic split: every `every`-th name is held out for testing."""
    test = names[::every]
    return [n for i, n in enumerate(names) if i % every], test


class Model:
    def __init__(self, order: int, k: float = 0.1) -> None:
        if order < 0 or k <= 0:
            raise MakerError("order must be >= 0 and smoothing k > 0")
        self.order, self.k = order, k
        self.counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.vocab: set[str] = {END}

    def fit(self, names: list[str]) -> Model:
        for n in names:
            s = START * self.order + n + END
            self.vocab.update(n)
            for i in range(self.order, len(s)):
                ctx = s[i - self.order:i] if self.order else ""
                self.counts[ctx][s[i]] += 1
        return self

    def _ctx(self, history: str) -> str:
        ctx = (START * self.order + history)[len(history):] if self.order else ""
        while ctx and ctx not in self.counts:  # back off to a shorter context we have seen
            ctx = ctx[1:]
        return ctx

    def prob(self, history: str, ch: str) -> float:
        c = self.counts.get(self._ctx(history), Counter())
        return (c[ch] + self.k) / (sum(c.values()) + self.k * (len(self.vocab) + 1))

    def bits_per_char(self, names: list[str]) -> float:
        """Average cross-entropy on names the model has not seen: lower is better."""
        total, n = 0.0, 0
        for name in names:
            for i, ch in enumerate(name + END):
                total -= math.log2(self.prob(name[:i], ch))
                n += 1
        return total / n

    def sample(self, rng: random.Random, prefix: str = "", max_len: int = 16) -> str:
        out = prefix
        while len(out) < max_len:
            c = self.counts.get(self._ctx(out), Counter())
            if not c:
                break
            chars = sorted(c)
            ch = rng.choices(chars, weights=[c[x] for x in chars])[0]
            if ch == END:
                break
            out += ch
        return out


def evaluate(names: list[str], orders: range = range(0, 5)) -> list[dict[str, float]]:
    train, test = split(names)
    return [{"order": o, "bits": round(Model(o).fit(train).bits_per_char(test), 3)} for o in orders]


def best_order(names: list[str]) -> int:
    return int(min(evaluate(names), key=lambda r: r["bits"])["order"])


@dataclass(frozen=True)
class Batch:
    names: list[str]
    attempts: int  # raw samples drawn to get these names


def generate(names: list[str], order: int, n: int, seed: int, prefix: str = "") -> Batch:
    """Names of 4-14 letters that are not in the training data."""
    if not 1 <= n <= 50:
        raise MakerError("n must be between 1 and 50")
    prefix = prefix.strip().lower()
    if not all(c.isalpha() or c == " " for c in prefix) or len(prefix) > 6:
        raise MakerError("prefix must be up to 6 letters")
    model = Model(order).fit(names)
    known = set(names)
    rng = random.Random(seed)
    out: list[str] = []
    tries = 0
    while len(out) < n and tries < n * 400:
        tries += 1
        w = model.sample(rng, prefix)
        if 4 <= len(w) <= 14 and w not in out:
            if w not in known:
                out.append(w)
    return Batch([w.title() for w in out], tries)
