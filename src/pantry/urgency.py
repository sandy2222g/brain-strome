"""Turn raw pantry entries into enriched items with a 0-1 urgency score."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from pantry.catalog import DEFAULT_STORAGE, OTHER, STORAGES, Ingredient, resolve, shelf_days
from pantry.waste_model import WasteModel

TIME_WEIGHT = 0.7
ML_WEIGHT = 0.3
DECAY_DAYS = 3.0


@dataclass
class RawItem:
    name: str
    expiry: date | None = None
    quantity: float = 1.0  # number of units (packs, pieces)
    storage: str | None = None
    purchased: date | None = None


@dataclass
class PantryItem:
    idx: int
    name: str
    canonical: str | None
    category: str
    storage: str
    quantity: float
    kg: float
    price_per_kg: float
    expiry: date
    days_left: int
    days_since_purchase: int
    p_waste: float
    urgency: float
    status: str


def time_urgency(days_left: int) -> float:
    """1.0 when due or past due, decaying exponentially: ~0.72 at 1 day, ~0.37 at 3, ~0.1 at 7."""
    return 1.0 if days_left <= 0 else math.exp(-days_left / DECAY_DAYS)


def status_for(days_left: int) -> str:
    if days_left < 0:
        return "expired"
    if days_left == 0:
        return "use today"
    if days_left <= 2:
        return "use soon"
    if days_left <= 7:
        return "this week"
    return "fine"


def ingredient_for(raw: RawItem) -> Ingredient:
    return resolve(raw.name) or OTHER


def enrich(raws: list[RawItem], today: date, household: int, model: WasteModel) -> list[PantryItem]:
    """Compute days left, spoilage probability and urgency for each item as of `today`."""
    prepared: list[tuple[int, RawItem, Ingredient, str, date, date]] = []
    for idx, raw in enumerate(raws):
        if raw.quantity <= 1e-6:
            continue
        ing = ingredient_for(raw)
        storage = raw.storage if raw.storage in STORAGES else DEFAULT_STORAGE[ing.category]
        shelf = shelf_days(ing.category, storage)
        if raw.expiry is not None:
            expiry = raw.expiry
            purchased = raw.purchased or min(today, expiry - timedelta(days=shelf))
        else:
            purchased = raw.purchased or today
            expiry = purchased + timedelta(days=shelf)
        prepared.append((idx, raw, ing, storage, expiry, purchased))
    if not prepared:
        return []
    rows = pd.DataFrame(
        {
            "category": [p[2].category for p in prepared],
            "storage": [p[3] for p in prepared],
            "days_since_purchase": [max(0, (today - p[5]).days) for p in prepared],
            "household_size": household,
        }
    )
    probs = model.predict_proba(rows)
    items: list[PantryItem] = []
    for (idx, raw, ing, storage, expiry, _), dsp, p in zip(prepared, rows["days_since_purchase"], probs, strict=True):
        left = (expiry - today).days
        urgency = TIME_WEIGHT * time_urgency(left) + ML_WEIGHT * float(p)
        items.append(
            PantryItem(
                idx=idx,
                name=raw.name,
                canonical=ing.name if ing is not OTHER else None,
                category=ing.category,
                storage=storage,
                quantity=raw.quantity,
                kg=round(raw.quantity * ing.unit_kg, 4),
                price_per_kg=ing.price_per_kg,
                expiry=expiry,
                days_left=left,
                days_since_purchase=int(dsp),
                p_waste=round(float(p), 4),
                urgency=round(urgency, 4),
                status=status_for(left),
            )
        )
    return items


def prioritize(items: list[PantryItem]) -> list[PantryItem]:
    """Most urgent first; expired items last (they are a safety check, not a cooking target)."""
    return sorted(items, key=lambda i: (i.days_left < 0, -i.urgency, i.days_left))
