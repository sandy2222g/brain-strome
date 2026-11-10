"""Turn messy bank descriptions into a stable merchant key."""
from __future__ import annotations

import re

NOISE = {
    "POS", "CARD", "PAYMENT", "TO", "DEBIT", "ONLINE", "PURCHASE", "RECURRING", "DD", "SO", "FP", "VIA",
    "LONDON", "LEEDS", "BRISTOL", "DUBLIN", "CORK", "UK", "IE", "GB",
}


def merchant_key(description: str) -> str:
    """Upper-case, drop reference numbers, card-terminal words and city names.

    'POS 927 STREAMBOX'          -> 'STREAMBOX'
    'FITPASS GYM*4821 LEEDS'     -> 'FITPASS GYM'
    'CARD PAYMENT TO MEALBOX 1234' -> 'MEALBOX'
    """
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", description.upper())
    tokens = [t for t in text.split() if not any(c.isdigit() for c in t) and t not in NOISE]
    return " ".join(tokens) or description.strip().upper()
