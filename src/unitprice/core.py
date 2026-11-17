"""Normalise pack sizes to grams (or millilitres) and rank by price per 100."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "products.json"
# factor to grams (mass) or millilitres (volume)
UNITS: dict[str, tuple[str, float]] = {
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "oz": ("mass", 28.3495),
    "lb": ("mass", 453.592),
    "ml": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "fl oz": ("volume", 29.5735),
}


class PriceError(ValueError):
    """Raised for invalid products or mixed kinds."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def per_100(product: dict[str, Any]) -> tuple[str, float]:
    """Return (kind, price per 100 g or 100 ml)."""
    unit = str(product["unit"]).lower()
    if unit not in UNITS:
        raise PriceError(f"unknown unit {unit!r}")
    price, qty = float(product["price"]), float(product["qty"])
    if price <= 0 or qty <= 0:
        raise PriceError(f"price and quantity must be positive for {product['name']!r}")
    kind, factor = UNITS[unit]
    return kind, price / (qty * factor) * 100


def rank(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not products:
        raise PriceError("need at least one product")
    rows = []
    kinds = set()
    for p in products:
        kind, unit_price = per_100(p)
        kinds.add(kind)
        rows.append({"name": p["name"], "price": float(p["price"]), "per_100": round(unit_price, 4)})
    if len(kinds) > 1:
        raise PriceError("cannot compare mass with volume")
    rows.sort(key=lambda r: (r["per_100"], r["name"]))
    best = rows[0]["per_100"]
    for r in rows:
        r["extra_pct"] = round((r["per_100"] / best - 1) * 100, 1)
    return rows


def largest_pack(products: list[dict[str, Any]]) -> str:
    """Baseline rule of thumb: the biggest pack is the cheapest per unit."""
    return max(products, key=lambda p: (UNITS[str(p["unit"]).lower()][1] * float(p["qty"]), p["name"]))["name"]
