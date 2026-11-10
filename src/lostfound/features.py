"""Pair features: how well does a found item fit a lost report?"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from lostfound.text import Attributes

# Rough campus map (x, y in 100 m units) so that "library" and "cafeteria" are close, "car park" is far.
PLACE_XY = {
    "main gate": (0, 0),
    "library": (4, 3),
    "cafeteria": (5, 4),
    "gym": (9, 1),
    "lab block": (3, 7),
    "lecture hall": (4, 5),
    "bus stop": (1, 0),
    "sports field": (10, 3),
    "dorm lobby": (7, 8),
    "car park": (0, 4),
}
FEATURE_NAMES = [
    "text_similarity",
    "same_category",
    "category_conflict",
    "same_color",
    "color_conflict",
    "same_brand",
    "brand_conflict",
    "extras_overlap",
    "found_before_lost",
    "days_gap",
    "place_distance",
]


@dataclass(frozen=True)
class Report:
    when: date
    place: str
    attrs: Attributes


def place_distance(a: str, b: str) -> float:
    pa, pb = PLACE_XY.get(a), PLACE_XY.get(b)
    return math.dist(pa, pb) if pa and pb else 6.0  # unknown place: assume fairly far


def pair_features(lost: Report, found: Report, text_sim: float) -> list[float]:
    la, fa = lost.attrs, found.attrs
    gap = (found.when - lost.when).days
    overlap = len(la.extras & fa.extras) / len(la.extras | fa.extras) if (la.extras | fa.extras) else 0.0
    return [
        text_sim,
        float(la.category is not None and la.category == fa.category),
        float(la.category is not None and fa.category is not None and la.category != fa.category),
        float(la.color is not None and la.color == fa.color),
        float(la.color is not None and fa.color is not None and la.color != fa.color),
        float(la.brand is not None and la.brand == fa.brand),
        float(la.brand is not None and fa.brand is not None and la.brand != fa.brand),
        overlap,
        float(gap < 0),
        float(min(max(gap, 0), 30)),
        place_distance(lost.place, found.place),
    ]


def explain(lost: Report, found: Report) -> list[str]:
    """Plain-language reasons for a candidate, shown next to the score."""
    la, fa = lost.attrs, found.attrs
    out: list[str] = []
    if la.category and la.category == fa.category:
        out.append(f"both are a {la.category}")
    if la.color and la.color == fa.color:
        out.append(f"same colour ({la.color})")
    if la.brand and la.brand == fa.brand:
        out.append(f"same brand ({la.brand})")
    if la.extras & fa.extras:
        out.append("matching details: " + ", ".join(sorted(la.extras & fa.extras)))
    gap = (found.when - lost.when).days
    if 0 <= gap <= 7:
        out.append(f"handed in {gap} day(s) after it went missing")
    d = place_distance(lost.place, found.place)
    if d <= 1.5:
        out.append("found at the same spot" if d == 0 else f"found close by ({found.place})")
    return out


def to_matrix(rows: list[list[float]]) -> np.ndarray:
    return np.asarray(rows, dtype=float)
