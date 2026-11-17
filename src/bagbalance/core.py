"""Partition items into two bags with the smallest weight difference (subset-sum DP)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "items.json"
STEP = 10  # grams are rounded to the nearest 10 g for the DP table


class BagError(ValueError):
    """Raised for invalid items."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _items(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(raw) < 2:
        raise BagError("need at least two items")
    out = []
    for r in raw:
        g = int(r["g"])
        if g <= 0:
            raise BagError(f"weight must be positive for {r['name']!r}")
        out.append({"name": str(r["name"]), "g": g})
    return out


def _result(items: list[dict[str, Any]], in_a: set[int]) -> dict[str, Any]:
    a = [items[i] for i in sorted(in_a)]
    b = [items[i] for i in range(len(items)) if i not in in_a]
    wa, wb = sum(x["g"] for x in a), sum(x["g"] for x in b)
    return {"bag_a": a, "bag_b": b, "weight_a": wa, "weight_b": wb, "difference": abs(wa - wb)}


def balance(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Best split: reachable subset sums in units of STEP g, closest to half; exact weights are then reported."""
    items = _items(raw)
    units = [max(1, round(x["g"] / STEP)) for x in items]
    total = sum(units)
    reach: dict[int, frozenset[int]] = {0: frozenset()}
    for i, u in enumerate(units):
        for s, chosen in list(reach.items()):
            if s + u not in reach:
                reach[s + u] = chosen | {i}
    target = min(reach, key=lambda s: (abs(total - 2 * s), s))
    best = _result(items, set(reach[target]))
    # rounding may leave a tiny gap; keep the lighter bag as A for stable output
    if best["weight_a"] > best["weight_b"]:
        best = _result(items, set(range(len(items))) - set(reach[target]))
    return best


def alternate(raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Baseline: alternate items between the bags in listed order."""
    items = _items(raw)
    return _result(items, {i for i in range(len(items)) if i % 2 == 0})


def over_limit(result: dict[str, Any], limit_g: int) -> list[str]:
    return [k for k in ("weight_a", "weight_b") if result[k] > limit_g]
