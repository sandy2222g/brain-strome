"""Multinomial Naive Bayes SMS spam filter written from scratch (no ML library).

Features: lower-cased word unigrams and bigrams plus three cheap shape features (contains URL,
contains digits, long ALL-CAPS word). Laplace smoothing; decisions use the log-odds with a tunable
threshold so precision and recall can be traded off.
"""

from __future__ import annotations

import csv
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
TOKEN = re.compile(r"[a-z0-9']+")


class SpamError(ValueError):
    """Invalid input."""


def features(text: str) -> list[str]:
    words = TOKEN.findall(text.lower())
    feats = list(words) + [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]
    if re.search(r"\b\w+\.(?:example|com|net|org)\b|https?://", text.lower()):
        feats.append("__url__")
    if re.search(r"\d", text):
        feats.append("__digit__")
    if any(len(w) >= 4 and w.isupper() for w in re.findall(r"[A-Za-z]+", text)):
        feats.append("__caps__")
    return feats


@dataclass
class NaiveBayes:
    alpha: float = 1.0
    counts: dict[str, Counter[str]] = field(default_factory=lambda: {"spam": Counter(), "ham": Counter()})
    docs: Counter[str] = field(default_factory=Counter)
    vocab: set[str] = field(default_factory=set)

    def fit(self, rows: list[tuple[str, str]]) -> NaiveBayes:
        if not rows:
            raise SpamError("no training data")
        for label, text in rows:
            if label not in ("spam", "ham"):
                raise SpamError(f"bad label: {label}")
            f = features(text)
            self.counts[label].update(f)
            self.docs[label] += 1
            self.vocab.update(f)
        if not self.docs["spam"] or not self.docs["ham"]:
            raise SpamError("need both spam and ham examples")
        return self

    def _logp(self, label: str, feats: list[str]) -> float:
        total = sum(self.counts[label].values()) + self.alpha * len(self.vocab)
        lp = math.log(self.docs[label] / sum(self.docs.values()))
        for f in feats:
            if f in self.vocab:
                lp += math.log((self.counts[label][f] + self.alpha) / total)
        return lp

    def log_odds(self, text: str) -> float:
        f = features(text)
        return self._logp("spam", f) - self._logp("ham", f)

    def prob_spam(self, text: str) -> float:
        z = max(-50.0, min(50.0, self.log_odds(text)))
        return 1 / (1 + math.exp(-z))

    def predict(self, text: str, threshold: float = 0.0) -> str:
        return "spam" if self.log_odds(text) > threshold else "ham"

    def explain(self, text: str, top: int = 5) -> list[tuple[str, float]]:
        """Features pushing the message hardest towards spam (positive) or ham (negative)."""
        total_s = sum(self.counts["spam"].values()) + self.alpha * len(self.vocab)
        total_h = sum(self.counts["ham"].values()) + self.alpha * len(self.vocab)
        out = {}
        for f in set(features(text)):
            if f in self.vocab:
                s = math.log((self.counts["spam"][f] + self.alpha) / total_s)
                h = math.log((self.counts["ham"][f] + self.alpha) / total_h)
                out[f] = s - h
        ranked = sorted(out.items(), key=lambda kv: -abs(kv[1]))
        return [(k, round(v, 2)) for k, v in ranked[:top]]


def load_csv(path: Path) -> list[tuple[str, str]]:
    with path.open() as f:
        return [(r["label"], r["text"]) for r in csv.DictReader(f)]


def split(rows: list[tuple[str, str]], frac: float = 0.8) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    k = int(len(rows) * frac)
    return rows[:k], rows[k:]


def evaluate(model: NaiveBayes, rows: list[tuple[str, str]], threshold: float = 0.0) -> dict[str, float]:
    tp = fp = fn = tn = 0
    for label, text in rows:
        pred = model.predict(text, threshold)
        if label == "spam":
            tp, fn = tp + (pred == "spam"), fn + (pred == "ham")
        else:
            fp, tn = fp + (pred == "spam"), tn + (pred == "ham")
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    return {
        "accuracy": round((tp + tn) / len(rows), 3),
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "false_positives": fp,
        "false_negatives": fn,
        "n": len(rows),
    }
