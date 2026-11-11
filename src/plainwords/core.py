"""Readability scoring and plain-language hints for short texts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "jargon.json"
LONG_SENTENCE = 25
BE = r"(?:is|are|was|were|be|been|being)"
PASSIVE = re.compile(rf"\b{BE}\s+(?:\w+ly\s+)?(\w+(?:ed|en))\b", re.I)
IRREGULAR = {"known", "shown", "given", "taken", "made", "done", "seen", "written", "sent", "held", "paid", "told"}


class TextError(ValueError):
    """Invalid input."""


def load_swaps(path: Path = DATA) -> dict[str, str]:
    return json.loads(path.read_text())["swaps"]


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if re.search(r"\w", p)]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text)


def syllables(word: str) -> int:
    """Vowel-group heuristic with silent-e and -le handling; at least 1."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    groups = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith("le") and groups > 1:
        groups -= 1
    if w.endswith("es") or w.endswith("ed"):
        if groups > 1 and not re.search(r"(?:t|d|s|x|z|ch|sh)e[sd]$", w):
            groups -= 1
    return max(1, groups)


@dataclass(frozen=True)
class Scores:
    words: int
    sentences: int
    avg_sentence_words: float
    avg_syllables: float
    reading_ease: float
    grade: float


def score(text: str) -> Scores:
    ss, ws = sentences(text), words(text)
    if not ws:
        raise TextError("write at least one word")
    syl = sum(syllables(w) for w in ws)
    wps, spw = len(ws) / max(len(ss), 1), syl / len(ws)
    ease = 206.835 - 1.015 * wps - 84.6 * spw
    grade = 0.39 * wps + 11.8 * spw - 15.59
    return Scores(len(ws), len(ss), round(wps, 1), round(spw, 2), round(ease, 1), round(grade, 1))


def label(ease: float) -> str:
    for cut, name in (
        (90, "very easy"),
        (80, "easy"),
        (70, "fairly easy"),
        (60, "plain"),
        (50, "fairly hard"),
        (30, "hard"),
    ):
        if ease >= cut:
            return name
    return "very hard"


def find_swaps(text: str, swaps: dict[str, str]) -> list[dict[str, str]]:
    out = []
    for phrase in sorted(swaps, key=len, reverse=True):
        for m in re.finditer(rf"\b{re.escape(phrase)}\b", text, re.I):
            out.append({"found": m.group(0), "use": swaps[phrase], "at": str(m.start())})
    return sorted(out, key=lambda d: int(d["at"]))


def is_passive(sentence: str) -> bool:
    for m in PASSIVE.finditer(sentence):
        w = m.group(1).lower()
        if w not in {"need", "indeed", "seed", "feed", "speed", "bleed", "breed", "hundred", "red", "bed", "shed"}:
            return True
    return any(re.search(rf"\b{BE}\s+{v}\b", sentence, re.I) for v in IRREGULAR)


def review(text: str) -> dict[str, object]:
    swaps = load_swaps()
    sc = score(text)
    rows = []
    for s in sentences(text):
        n = len(words(s))
        rows.append(
            {
                "text": s,
                "words": n,
                "long": n > LONG_SENTENCE,
                "passive": is_passive(s),
                "swaps": find_swaps(s, swaps),
            }
        )
    return {
        "scores": sc.__dict__,
        "label": label(sc.reading_ease),
        "sentences": rows,
        "counts": {
            "long": sum(r["long"] for r in rows),
            "passive": sum(r["passive"] for r in rows),
            "swaps": sum(len(r["swaps"]) for r in rows),
        },
    }
