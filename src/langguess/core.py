"""Language identification with smoothed character n-gram models (naive Bayes over n-grams)."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "sentences.json"
TRAIN_N = 14  # sentences per language used for training; the remaining 6 are held out
ALPHA = 0.5


class LangError(ValueError):
    """Invalid input."""


def grams(text: str, n: int) -> list[str]:
    t = " " + " ".join(text.lower().split()) + " "
    return [t[i : i + n] for i in range(len(t) - n + 1)]


class Model:
    def __init__(self, corpus: dict[str, list[str]], n: int = 3) -> None:
        if len(corpus) < 2:
            raise LangError("need at least two languages")
        self.n = n
        self.counts = {lang: Counter(g for s in sents for g in grams(s, n)) for lang, sents in corpus.items()}
        self.totals = {lang: sum(c.values()) for lang, c in self.counts.items()}
        self.vocab = len(set().union(*self.counts.values())) + 1  # +1 for unseen grams

    def scores(self, text: str) -> dict[str, float]:
        gs = grams(text, self.n)
        if not text.strip() or not gs:
            raise LangError("text must contain at least one character")
        return {lang: sum(math.log((c[g] + ALPHA) / (self.totals[lang] + ALPHA * self.vocab)) for g in gs)
                for lang, c in self.counts.items()}

    def guess(self, text: str) -> dict[str, object]:
        s = self.scores(text)
        m = max(s.values())
        z = sum(math.exp(v - m) for v in s.values())
        probs = {lang: math.exp(v - m) / z for lang, v in s.items()}
        ranked = sorted(probs.items(), key=lambda kv: -kv[1])
        return {"language": ranked[0][0], "confidence": round(ranked[0][1], 3),
                "ranking": [{"language": k, "p": round(v, 3)} for k, v in ranked]}


def load(path: Path = DATA) -> dict[str, list[str]]:
    return json.loads(path.read_text())  # type: ignore[no-any-return]


def split(corpus: dict[str, list[str]]) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    train = {lang: s[:TRAIN_N] for lang, s in corpus.items()}
    test = [(lang, sent) for lang, s in corpus.items() for sent in s[TRAIN_N:]]
    return train, test


def accuracy(model: Model, test: list[tuple[str, str]], prefix: int | None = None) -> float:
    ok = sum(model.guess(s[:prefix] if prefix else s)["language"] == lang for lang, s in test)
    return ok / len(test)


def evaluate() -> dict[str, object]:
    train, test = split(load())
    tri, uni = Model(train, 3), Model(train, 1)
    return {"languages": sorted(train), "train_sentences": TRAIN_N * len(train), "test_sentences": len(test),
            "trigram": round(accuracy(tri, test), 3), "unigram": round(accuracy(uni, test), 3),
            "trigram_short": round(accuracy(tri, test, 20), 3), "unigram_short": round(accuracy(uni, test, 20), 3),
            "chance": round(1 / len(train), 3)}


def full_model() -> Model:
    return Model(load(), 3)
