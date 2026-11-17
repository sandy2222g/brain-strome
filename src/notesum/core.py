"""Extractive meeting summaries with TextRank, plus action-item extraction (invented meetings)."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "meetings.json"
STOP = frozenset(
    "a an the to of in on at for from and or it be is are was were we our us i you they that this with as by "
    "so will should about have has had not no".split()
)
DAMPING = 0.85
ACTION = re.compile(r"\b([A-Z][a-z]+) (?:will|should) (.+?)(?: (?:by|before) ([A-Za-z ]+?))?\.?$")
NOT_PEOPLE = frozenset({"The", "This", "That", "It", "We", "Everyone", "Someone", "There", "They", "Let", "Our"})


class NotesError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def sentences(text: str) -> list[str]:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if not parts:
        raise NotesError("no text")
    return parts


def words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]


def similarity_matrix(sents: list[str]) -> list[list[float]]:
    """TF-IDF cosine similarity between every pair of sentences (diagonal is zero)."""
    docs = [Counter(words(s)) for s in sents]
    n = len(docs)
    df = Counter(w for d in docs for w in d)
    idf = {w: math.log((1 + n) / (1 + c)) + 1 for w, c in df.items()}
    vecs = [{w: c * idf[w] for w, c in d.items()} for d in docs]
    norms = [math.sqrt(sum(x * x for x in v.values())) for v in vecs]
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if norms[i] and norms[j]:
                dot = sum(x * vecs[j].get(w, 0.0) for w, x in vecs[i].items())
                sim[i][j] = sim[j][i] = dot / (norms[i] * norms[j])
    return sim


def textrank(sim: list[list[float]], iters: int = 100, tol: float = 1e-9) -> list[float]:
    """PageRank power iteration on the sentence-similarity graph."""
    n = len(sim)
    out = [sum(row) for row in sim]
    score = [1.0 / n] * n
    for _ in range(iters):
        new = [
            (1 - DAMPING) / n + DAMPING * sum(sim[j][i] / out[j] * score[j] for j in range(n) if out[j] > 0)
            for i in range(n)
        ]
        if sum(abs(a - b) for a, b in zip(new, score, strict=True)) < tol:
            score = new
            break
        score = new
    return score


def summarise(text: str, k: int = 3) -> dict[str, Any]:
    if k < 1:
        raise NotesError("k must be at least 1")
    sents = sentences(text)
    k = min(k, len(sents))
    score = textrank(similarity_matrix(sents))
    top = sorted(sorted(range(len(sents)), key=lambda i: (-score[i], i))[:k])  # keep the original order
    return {"indices": top, "summary": [sents[i] for i in top], "scores": [round(s, 4) for s in score]}


def lead_k(text: str, k: int = 3) -> list[int]:
    """Baseline: the first k sentences."""
    return list(range(min(k, len(sentences(text)))))


def action_items(text: str) -> list[dict[str, str | None]]:
    items = []
    for s in sentences(text):
        m = ACTION.search(s)
        if m and m.group(1) not in NOT_PEOPLE:
            items.append({"owner": m.group(1), "task": m.group(2).strip(), "due": m.group(3)})
    return items


def precision(chosen: list[int], key: list[int]) -> float:
    return len(set(chosen) & set(key)) / len(chosen)


def evaluate(k: int = 3) -> dict[str, Any]:
    ms = load()["meetings"]
    tr = [precision(summarise(m["text"], k)["indices"], m["key"]) for m in ms]
    lead = [precision(lead_k(m["text"], k), m["key"]) for m in ms]
    return {
        "meetings": len(ms),
        "textrank_precision": round(sum(tr) / len(tr), 3),
        "lead_precision": round(sum(lead) / len(lead), 3),
        "per_meeting": [
            {"title": m["title"], "textrank": round(a, 2), "lead": round(b, 2)}
            for m, a, b in zip(ms, tr, lead, strict=True)
        ],
    }
