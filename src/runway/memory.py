"""A minimal forgetting-curve model.

Retention after `t` days since the last review is R(t) = exp(-t / S), where S is the
memory *stability* in days. Reviewing a topic increases S, and the lower the retention at
review time the larger the gain (desirable difficulty), which is what produces
expanding review intervals.
"""
from __future__ import annotations

import math


def retention(days_since_review: float, stability: float) -> float:
    """Probability of recalling the topic after `days_since_review` days."""
    if stability <= 0:
        raise ValueError("stability must be positive")
    return math.exp(-max(days_since_review, 0.0) / stability)


def initial_stability(confidence: float, difficulty: float) -> float:
    """Stability (days) before any planned study. confidence and difficulty are in [0, 1]."""
    if not (0.0 <= confidence <= 1.0 and 0.0 <= difficulty <= 1.0):
        raise ValueError("confidence and difficulty must be within [0, 1]")
    return max(0.8, (1.0 + 6.0 * confidence) * (1.3 - 0.6 * difficulty))


def review(stability: float, retention_at_review: float, difficulty: float) -> float:
    """New stability after a review session."""
    gain = 1.6 + 1.4 * (1.0 - retention_at_review)  # between 1.6x and 3.0x
    gain *= 1.0 - 0.25 * difficulty  # harder material consolidates more slowly
    return stability * max(gain, 1.2)


def next_review_in(stability: float, target_retention: float = 0.8) -> float:
    """Days until retention decays to `target_retention`."""
    if not 0.0 < target_retention < 1.0:
        raise ValueError("target_retention must be in (0, 1)")
    return -stability * math.log(target_retention)
