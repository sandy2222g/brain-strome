"""Ingredient catalog: categories, shelf-life rules, price and weight table, name normalisation.

All numbers are rough, original approximations (typical European/US supermarket values), not sourced data.
"""
from __future__ import annotations

from dataclasses import dataclass

STORAGES = ("fridge", "pantry", "freezer")

# Shelf life in days per category and storage place.
SHELF_DAYS: dict[str, dict[str, int]] = {
    "leafy": {"fridge": 6, "pantry": 2, "freezer": 60},
    "herb": {"fridge": 7, "pantry": 2, "freezer": 90},
    "produce": {"fridge": 10, "pantry": 5, "freezer": 180},
    "root": {"fridge": 30, "pantry": 21, "freezer": 180},
    "dairy": {"fridge": 12, "pantry": 1, "freezer": 90},
    "egg": {"fridge": 28, "pantry": 10, "freezer": 180},
    "meat": {"fridge": 3, "pantry": 1, "freezer": 150},
    "seafood": {"fridge": 2, "pantry": 1, "freezer": 120},
    "bakery": {"fridge": 7, "pantry": 5, "freezer": 90},
    "grain": {"fridge": 365, "pantry": 365, "freezer": 365},
    "canned": {"fridge": 540, "pantry": 540, "freezer": 540},
    "frozen": {"fridge": 2, "pantry": 1, "freezer": 240},
    "other": {"fridge": 14, "pantry": 14, "freezer": 90},
}
DEFAULT_STORAGE: dict[str, str] = {
    "leafy": "fridge", "herb": "fridge", "produce": "fridge", "root": "pantry", "dairy": "fridge",
    "egg": "fridge", "meat": "fridge", "seafood": "fridge", "bakery": "pantry", "grain": "pantry",
    "canned": "pantry", "frozen": "freezer", "other": "pantry",
}  # fmt: skip
CATEGORIES = tuple(SHELF_DAYS)

# Staples assumed to be always at home; they never count as missing.
STAPLES = frozenset({"salt", "pepper", "olive oil", "oil", "flour", "sugar", "water", "spice", "vinegar"})


@dataclass(frozen=True)
class Ingredient:
    name: str
    category: str
    price_per_kg: float  # currency units per kg (currency-neutral)
    unit_kg: float  # weight of one typical unit (one onion, one pack of yogurt ...)
    portion_kg: float  # amount a typical recipe uses


def _i(name: str, cat: str, price: float, unit: float, portion: float) -> Ingredient:
    return Ingredient(name, cat, price, unit, portion)


INGREDIENTS: list[Ingredient] = [
    _i("tomato", "produce", 4.5, 0.15, 0.15), _i("bell pepper", "produce", 5, 0.2, 0.15),
    _i("zucchini", "produce", 3, 0.25, 0.2), _i("broccoli", "produce", 4, 0.4, 0.2),
    _i("mushroom", "produce", 7, 0.25, 0.15), _i("lemon", "produce", 4, 0.1, 0.05),
    _i("apple", "produce", 3, 0.18, 0.18), _i("banana", "produce", 2, 0.12, 0.12),
    _i("cucumber", "produce", 3, 0.3, 0.15), _i("avocado", "produce", 8, 0.2, 0.15),
    _i("cauliflower", "produce", 3.5, 0.6, 0.25), _i("green bean", "produce", 6, 0.3, 0.15),
    _i("eggplant", "produce", 4, 0.3, 0.25),
    _i("spinach", "leafy", 8, 0.2, 0.1), _i("lettuce", "leafy", 5, 0.3, 0.1),
    _i("basil", "herb", 30, 0.03, 0.01), _i("cilantro", "herb", 30, 0.03, 0.01),
    _i("parsley", "herb", 25, 0.03, 0.01),
    _i("onion", "root", 2, 0.15, 0.1), _i("garlic", "root", 8, 0.05, 0.01),
    _i("potato", "root", 1.8, 0.2, 0.2), _i("carrot", "root", 1.5, 0.1, 0.1),
    _i("sweet potato", "root", 2.5, 0.25, 0.25), _i("ginger", "root", 10, 0.1, 0.02),
    _i("cabbage", "root", 1.5, 0.9, 0.2),
    _i("milk", "dairy", 1.2, 1.0, 0.25), _i("yogurt", "dairy", 3, 0.5, 0.15),
    _i("cheddar", "dairy", 12, 0.2, 0.05), _i("mozzarella", "dairy", 10, 0.25, 0.1),
    _i("butter", "dairy", 9, 0.25, 0.02), _i("cream", "dairy", 6, 0.25, 0.1),
    _i("parmesan", "dairy", 20, 0.15, 0.03), _i("feta", "dairy", 12, 0.2, 0.08),
    _i("egg", "egg", 4, 0.06, 0.12),
    _i("chicken breast", "meat", 9, 0.5, 0.2), _i("ground beef", "meat", 11, 0.45, 0.2),
    _i("bacon", "meat", 14, 0.25, 0.06), _i("sausage", "meat", 9, 0.4, 0.2), _i("ham", "meat", 12, 0.2, 0.08),
    _i("salmon", "seafood", 18, 0.3, 0.15), _i("shrimp", "seafood", 16, 0.3, 0.15),
    _i("bread", "bakery", 4, 0.5, 0.1), _i("tortilla", "bakery", 6, 0.3, 0.1),
    _i("rice", "grain", 2.2, 1.0, 0.1), _i("pasta", "grain", 2.5, 0.5, 0.1), _i("oats", "grain", 3, 0.5, 0.06),
    _i("couscous", "grain", 4, 0.5, 0.08), _i("quinoa", "grain", 7, 0.5, 0.08),
    _i("canned tomato", "canned", 2.5, 0.4, 0.2), _i("chickpea", "canned", 3, 0.4, 0.2),
    _i("black bean", "canned", 3, 0.4, 0.2), _i("coconut milk", "canned", 4, 0.4, 0.2),
    _i("canned tuna", "canned", 12, 0.15, 0.12), _i("lentil", "canned", 3, 0.5, 0.1),
    _i("peanut butter", "canned", 6, 0.35, 0.03), _i("soy sauce", "canned", 5, 0.25, 0.02),
    _i("frozen pea", "frozen", 3, 0.5, 0.1), _i("frozen corn", "frozen", 3, 0.5, 0.1),
]  # fmt: skip

OTHER = Ingredient("other", "other", 5.0, 0.2, 0.1)


def normalize(name: str) -> str:
    """Lowercase, trim and singularise each word so 'Tomatoes' and 'tomato' match."""
    words = []
    for w in name.lower().replace("-", " ").split():
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith(("oes", "ches", "shes")):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith(("ss", "us")):
            w = w[:-1]
        words.append(w)
    return " ".join(words)


CATALOG: dict[str, Ingredient] = {normalize(i.name): i for i in INGREDIENTS}


def resolve(name: str) -> Ingredient | None:
    """Map a free-text item name to a catalog ingredient (exact match, else longest contained name)."""
    key = normalize(name)
    if key in CATALOG:
        return CATALOG[key]
    padded = f" {key} "
    best = max((k for k in CATALOG if f" {k} " in padded), key=len, default=None)
    return CATALOG[best] if best else None


def shelf_days(category: str, storage: str) -> int:
    return SHELF_DAYS.get(category, SHELF_DAYS["other"])[storage]
