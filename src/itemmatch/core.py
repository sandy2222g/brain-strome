"""Match typed shopping-list items to a store catalogue despite typos (edit distance with transpositions).

An item matches the closest catalogue name if the distance is within a third of its length (min 1);
otherwise it is reported as unmatched rather than guessed.
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "shop.json"


class MatchError(ValueError):
    """Invalid catalogue or list."""


def levenshtein(a: str, b: str) -> int:
    """Edit distance with adjacent transpositions (optimal string alignment): 'mlik' -> 'milk' costs 1."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def normalise(s: str) -> str:
    return " ".join(s.lower().split())


def build(catalogue: list[str], items: list[str]) -> tuple[list[str], list[str]]:
    if not catalogue or not items or len(catalogue) > 500 or len(items) > 100:
        raise MatchError("need a catalogue (max 500) and items (max 100)")
    cat = [normalise(c) for c in catalogue]
    if len(set(cat)) != len(cat):
        raise MatchError("catalogue names must be unique")
    return cat, [normalise(i) for i in items]


def best_match(item: str, catalogue: list[str]) -> tuple[str | None, int]:
    """Closest catalogue name (ties: first listed) or None if too far; also returns the distance."""
    dist, name = min((levenshtein(item, c), c) for c in catalogue)
    limit = max(1, len(item) // 3)
    return (name if dist <= limit else None), dist


def exact_match(item: str, catalogue: list[str]) -> str | None:
    return item if item in catalogue else None


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
