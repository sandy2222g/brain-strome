"""TF-IDF cosine search over FAQ entries, written from scratch, with a measured baseline (invented FAQ)."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "faq.json"
STOP = frozenset(
    "a an the to of in on at for from my me i do how can is are was what where who when which and or it be with "
    "about this that there your you should if".split()
)
QUESTION_WEIGHT = 2  # the question text counts double against the answer text


class SearchError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def stem(word: str) -> str:
    """Very light suffix stripping so renew / renewing / renewed meet."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


class Index:
    def __init__(self, faqs: list[dict[str, Any]]) -> None:
        if not faqs:
            raise SearchError("no FAQ entries")
        self.faqs = faqs
        docs = [tokens(f["q"]) * QUESTION_WEIGHT + tokens(f["a"]) for f in faqs]
        n = len(docs)
        df = Counter(w for d in docs for w in set(d))
        self.idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}  # smoothed idf
        self.vecs = [self._vector(Counter(d)) for d in docs]

    def _vector(self, counts: Counter[str]) -> dict[str, float]:
        v = {w: (1 + math.log(c)) * self.idf[w] for w, c in counts.items() if w in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values()))
        return {w: x / norm for w, x in v.items()} if norm else {}

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        q = self._vector(Counter(tokens(query)))
        if not q:
            raise SearchError("no recognisable words in the query")
        scored = [(sum(x * v.get(w, 0.0) for w, x in q.items()), f) for f, v in zip(self.faqs, self.vecs, strict=True)]
        scored.sort(key=lambda s: (-s[0], s[1]["id"]))
        return [
            {"id": f["id"], "question": f["q"], "answer": f["a"], "score": round(s, 3)}
            for s, f in scored[:k]
            if s > 0
        ]


def overlap_search(faqs: list[dict[str, Any]], query: str, k: int = 3) -> list[int]:
    """Baseline: rank by how many query words appear in the entry, no weighting."""
    q = set(tokens(query))
    scored = [(len(q & set(tokens(f["q"] + " " + f["a"]))), f["id"]) for f in faqs]
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [i for s, i in scored[:k] if s > 0]


def evaluate() -> dict[str, float | int]:
    data = load()
    idx = Index(data["faqs"])
    qs = data["queries"]

    def score(rank: Any) -> tuple[float, float, float]:
        top1 = top3 = mrr = 0.0
        for q in qs:
            ids = rank(q["text"])
            top1 += bool(ids) and ids[0] == q["id"]
            top3 += q["id"] in ids
            mrr += 1 / (ids.index(q["id"]) + 1) if q["id"] in ids else 0
        n = len(qs)
        return top1 / n, top3 / n, mrr / n

    def tfidf_ids(text: str) -> list[int]:
        try:
            return [r["id"] for r in idx.search(text, 3)]
        except SearchError:  # no query word appears anywhere in the FAQ: nothing to return
            return []

    t = score(tfidf_ids)
    b = score(lambda x: overlap_search(data["faqs"], x, 3))
    return {
        "queries": len(qs),
        "tfidf_top1": round(t[0], 3), "tfidf_top3": round(t[1], 3), "tfidf_mrr": round(t[2], 3),
        "overlap_top1": round(b[0], 3), "overlap_top3": round(b[1], 3), "overlap_mrr": round(b[2], 3),
    }
