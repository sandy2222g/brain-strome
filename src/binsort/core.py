"""Multinomial naive Bayes (from scratch) that maps a household item to the right bin (invented labels)."""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "items.csv"
ALPHA = 1.0  # Laplace smoothing


class SortError(ValueError):
    """Raised for invalid input."""


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def load_rows() -> list[tuple[str, str]]:
    with DATA.open(newline="") as fh:
        return [(r["item"], r["bin"]) for r in csv.DictReader(fh)]


def split(rows: list[tuple[str, str]], every: int = 4) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Deterministic stratified split: within each bin, every `every`-th row goes to the test set."""
    seen: Counter[str] = Counter()
    train, test = [], []
    for item, label in rows:
        seen[label] += 1
        (test if seen[label] % every == 0 else train).append((item, label))
    return train, test


class NaiveBayes:
    """Bag-of-words multinomial naive Bayes with Laplace smoothing, computed in log space."""

    def __init__(self) -> None:
        self.classes: list[str] = []
        self.prior: dict[str, float] = {}
        self.counts: dict[str, Counter[str]] = {}
        self.totals: dict[str, int] = {}
        self.vocab: set[str] = set()

    def fit(self, rows: list[tuple[str, str]]) -> NaiveBayes:
        if not rows:
            raise SortError("no training rows")
        labels = Counter(label for _, label in rows)
        self.classes = sorted(labels)
        self.counts = {c: Counter() for c in self.classes}
        for text, label in rows:
            self.counts[label].update(tokens(text))
        self.totals = {c: sum(self.counts[c].values()) for c in self.classes}
        self.vocab = {w for c in self.classes for w in self.counts[c]}
        self.prior = {c: math.log(labels[c] / len(rows)) for c in self.classes}
        return self

    def proba(self, text: str) -> dict[str, float]:
        words = tokens(text)
        if not words:
            raise SortError("describe the item with at least one word")
        v = len(self.vocab)
        logp = {}
        for c in self.classes:
            lp = self.prior[c]
            for w in words:
                lp += math.log((self.counts[c][w] + ALPHA) / (self.totals[c] + ALPHA * v))
            logp[c] = lp
        top = max(logp.values())
        exp = {c: math.exp(lp - top) for c, lp in logp.items()}
        z = sum(exp.values())
        return {c: exp[c] / z for c in self.classes}

    def predict(self, text: str) -> str:
        p = self.proba(text)
        return max(self.classes, key=lambda c: (p[c], c))


def accuracy(model: NaiveBayes, rows: list[tuple[str, str]]) -> float:
    return sum(model.predict(t) == y for t, y in rows) / len(rows)


def majority_accuracy(train: list[tuple[str, str]], test: list[tuple[str, str]]) -> float:
    """Baseline: always answer the most common training bin."""
    top = Counter(y for _, y in train).most_common(1)[0][0]
    return sum(y == top for _, y in test) / len(test)


def evaluate() -> dict[str, float | int]:
    train, test = split(load_rows())
    model = NaiveBayes().fit(train)
    return {
        "train": len(train),
        "test": len(test),
        "naive_bayes": round(accuracy(model, test), 3),
        "majority": round(majority_accuracy(train, test), 3),
    }


def trained() -> NaiveBayes:
    return NaiveBayes().fit(load_rows())
