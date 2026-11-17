"""Trie autocomplete: exact-prefix ranking plus Levenshtein-bounded fuzzy fallback."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "cities.csv"


class SearchError(ValueError):
    """Invalid input."""


@dataclass
class Node:
    kids: dict[str, Node] = field(default_factory=dict)
    word: str | None = None
    score: int = 0


class Trie:
    def __init__(self) -> None:
        self.root = Node()
        self.size = 0

    def add(self, word: str, score: int) -> None:
        node = self.root
        for ch in word.lower():
            node = node.kids.setdefault(ch, Node())
        if node.word is None:
            self.size += 1
        node.word, node.score = word, score

    def _collect(self, node: Node) -> list[tuple[str, int]]:
        out: list[tuple[str, int]] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if n.word is not None:
                out.append((n.word, n.score))
            stack.extend(n.kids.values())
        return out

    def prefix(self, q: str, k: int = 5) -> list[tuple[str, int]]:
        node = self.root
        for ch in q.lower():
            if ch not in node.kids:
                return []
            node = node.kids[ch]
        return sorted(self._collect(node), key=lambda t: (-t[1], t[0]))[:k]

    def fuzzy(self, q: str, max_dist: int = 1, k: int = 5) -> list[tuple[str, int, int]]:
        """Words having a prefix within `max_dist` edits of q; best (distance, -score) first."""
        q = q.lower()
        best: dict[str, tuple[int, int]] = {}

        def walk(node: Node, ch: str, prev: list[int]) -> None:
            row = [prev[0] + 1]
            for i in range(1, len(q) + 1):
                row.append(min(row[i - 1] + 1, prev[i] + 1, prev[i - 1] + (q[i - 1] != ch)))
            if row[-1] <= max_dist:
                for w, s in self._collect(node):
                    d = best.get(w, (max_dist + 1, 0))[0]
                    if row[-1] < d:
                        best[w] = (row[-1], s)
            if min(row) <= max_dist:
                for c, child in node.kids.items():
                    walk(child, c, row)

        first = list(range(len(q) + 1))
        for c, child in self.root.kids.items():
            walk(child, c, first)
        ranked = sorted(((w, d, s) for w, (d, s) in best.items()), key=lambda t: (t[1], -t[2], t[0]))
        return ranked[:k]

    def suggest(self, q: str, k: int = 5) -> dict[str, object]:
        if not q.strip():
            raise SearchError("query must not be empty")
        if not 1 <= k <= 20:
            raise SearchError("k must be within 1..20")
        q = q.strip()
        exact = self.prefix(q, k)
        if exact:  # fuzzy matching only kicks in when the typed text matches no name prefix
            return {"mode": "prefix", "results": [{"name": w, "score": s, "edits": 0} for w, s in exact]}
        found = self.fuzzy(q, 1 if len(q) <= 4 else 2, k)
        return {"mode": "fuzzy", "results": [{"name": w, "score": s, "edits": d} for w, d, s in found]}


def load(path: Path = DATA) -> Trie:
    t = Trie()
    with path.open() as fh:
        for r in csv.DictReader(fh):
            t.add(r["name"], int(r["score"]))
    return t


def typo(word: str, kind: int) -> str:
    """Deterministic typos at position 3: delete, swap, substitute, insert."""
    w = word.lower()
    i = min(3, len(w) - 2)
    if kind == 0:
        return w[:i] + w[i + 1 :]
    if kind == 1:
        return w[:i] + w[i + 1] + w[i] + w[i + 2 :]
    if kind == 2:
        return w[:i] + ("z" if w[i] != "z" else "q") + w[i + 1 :]
    return w[:i] + "x" + w[i:]


def evaluate(k: int = 5) -> dict[str, float]:
    """Recall@k on typo'd versions of every name: prefix-only baseline vs trie fuzzy."""
    t = load()
    names = [w for w, _ in t._collect(t.root) if len(w) >= 5]
    base = hit = n = 0
    for w in names:
        for kind in range(4):
            q = typo(w, kind)
            n += 1
            base += w in [x for x, _ in t.prefix(q, k)]
            hit += w in [r["name"] for r in t.suggest(q, k)["results"]]  # type: ignore[union-attr]
    return {"queries": n, "baseline_recall": round(base / n, 3), "fuzzy_recall": round(hit / n, 3)}
