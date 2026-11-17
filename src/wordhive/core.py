"""Find words that use only the hive letters and always include the centre letter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "hive.json"
MIN_LEN = 4


class HiveError(ValueError):
    """Raised for an invalid hive."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def check_hive(letters: str, center: str) -> tuple[frozenset[str], str]:
    letters = letters.lower()
    center = center.lower()
    if len(letters) != 7 or len(set(letters)) != 7 or not letters.isalpha():
        raise HiveError("a hive needs exactly 7 different letters")
    if len(center) != 1 or center not in letters:
        raise HiveError("the centre letter must be one of the 7 letters")
    return frozenset(letters), center


def is_pangram(word: str, letters: frozenset[str]) -> bool:
    return set(word) >= letters


def score(word: str, letters: frozenset[str]) -> int:
    """4 letters = 1 point, longer words one point per letter, pangrams +7."""
    base = 1 if len(word) == MIN_LEN else len(word)
    return base + (7 if is_pangram(word, letters) else 0)


def solve(words: list[str], letters: str, center: str) -> dict[str, Any]:
    allowed, mid = check_hive(letters, center)
    found = sorted(
        {w.lower() for w in words if len(w) >= MIN_LEN and mid in w.lower() and set(w.lower()) <= allowed},
        key=lambda w: (-score(w, allowed), w),
    )
    rows = [{"word": w, "points": score(w, allowed), "pangram": is_pangram(w, allowed)} for w in found]
    return {"words": rows, "count": len(rows), "total_points": sum(r["points"] for r in rows),
            "pangrams": [r["word"] for r in rows if r["pangram"]]}


def rank(points: int, total: int) -> str:
    """Rank label from the share of possible points reached."""
    share = points / total if total else 0
    for floor, name in ((0.7, "Genius"), (0.5, "Great"), (0.25, "Good"), (0.1, "Nice")):
        if share >= floor:
            return name
    return "Beginner"
