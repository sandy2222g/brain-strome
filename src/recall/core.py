"""Compare flashcard review schedules by simulating a learner who forgets.

Learner model (an assumption, stated plainly): the chance of recalling a card after `gap` days is exp(-gap / S)
where S is the card's memory stability in days. A successful review multiplies S by (1 + 2 / hardness); a failed
one cuts it to 40% (never below half a day). Harder cards (larger hardness) gain less from each review.

Four schedules decide when each card is next shown: daily, fixed (every 3 days), Leitner boxes (1, 2, 4, 8, 16, 32 days;
a miss sends the card back to box one) and a simplified SM-2 (intervals 1, 3, then growing by an ease factor that
drops after misses). Each is simulated over many seeds; we report reviews done and how well the deck is
remembered on the final day.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "deck.json"
STRATEGIES = ("daily", "fixed", "leitner", "sm2")
LEITNER_DAYS = (1, 2, 4, 8, 16, 32)
MAX_CARDS = 200


class DeckError(ValueError):
    """Invalid deck or settings."""


@dataclass(frozen=True)
class Card:
    name: str
    hardness: float  # 0.5 (easy) .. 3 (hard)


def build(cards: list[Card], days: int) -> tuple[list[Card], int]:
    if not 1 <= len(cards) <= MAX_CARDS:
        raise DeckError(f"between 1 and {MAX_CARDS} cards")
    if not 7 <= days <= 365:
        raise DeckError("days must be between 7 and 365")
    if len({c.name for c in cards}) != len(cards):
        raise DeckError("card names must be unique")
    if any(not 0.5 <= c.hardness <= 3 for c in cards):
        raise DeckError("hardness must be between 0.5 and 3")
    return cards, days


def load(path: Path = DATA) -> tuple[list[Card], int]:
    raw = json.loads(path.read_text())
    return build([Card(c["name"], c["hardness"]) for c in raw["cards"]], raw["days"])


@dataclass
class _State:
    stability: float = 1.0
    last: int = 0
    due: int = 0
    box: int = 0
    reps: int = 0
    interval: int = 1
    ease: float = 2.5


def _recall_p(gap: int, stability: float) -> float:
    return math.exp(-gap / stability)


def _simulate(strategy: str, cards: list[Card], days: int, seed: int) -> tuple[int, float]:
    if strategy not in STRATEGIES:
        raise DeckError(f"unknown strategy '{strategy}'")
    rng = random.Random(seed)
    states = [_State() for _ in cards]
    reviews = 0
    for day in range(days):
        for card, st in zip(cards, states, strict=True):
            if st.due > day:
                continue
            reviews += 1
            first = st.reps == 0
            ok = first or rng.random() < _recall_p(day - st.last, st.stability)
            if ok:
                st.stability *= 1 + 2 / card.hardness
            else:
                st.stability = max(0.5, st.stability * 0.4)
            st.last, st.reps = day, st.reps + 1
            if strategy == "daily":
                st.due = day + 1
            elif strategy == "fixed":
                st.due = day + 3
            elif strategy == "leitner":
                st.box = min(st.box + 1, len(LEITNER_DAYS) - 1) if ok else 0
                st.due = day + LEITNER_DAYS[st.box]
            else:
                if not ok:
                    st.interval, st.ease = 1, max(1.3, st.ease - 0.2)
                elif st.reps <= 2:
                    st.interval = 1 if st.reps == 1 else 3
                else:
                    st.interval = max(1, round(st.interval * st.ease))
                st.due = day + st.interval
    final = sum(_recall_p(days - st.last, st.stability) for st in states) / len(states)
    return reviews, final


def compare(cards: list[Card], days: int, seeds: int = 40) -> dict[str, dict[str, float]]:
    """Average reviews and final-day expected recall for every strategy over `seeds` simulated learners."""
    out: dict[str, dict[str, float]] = {}
    for s in STRATEGIES:
        runs = [_simulate(s, cards, days, seed) for seed in range(seeds)]
        out[s] = {
            "reviews": sum(r for r, _ in runs) / seeds,
            "reviews_per_card": sum(r for r, _ in runs) / seeds / len(cards),
            "recall": sum(f for _, f in runs) / seeds,
        }
    return out
