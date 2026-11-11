"""Scale recipes to a headcount and turn them into a shopping list priced by whole packs."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "recipes.json"


class CookError(ValueError):
    """Invalid request."""


@dataclass(frozen=True)
class Pack:
    size: float
    unit: str
    price: float


@dataclass(frozen=True)
class Recipe:
    name: str
    serves: int
    items: dict[str, float]


@dataclass(frozen=True)
class Line:
    item: str
    needed: float
    unit: str
    packs: int
    cost: float
    leftover: float


def load(path: Path = DATA) -> tuple[dict[str, Pack], dict[str, Recipe]]:
    raw = json.loads(path.read_text())
    packs = {k: Pack(**v) for k, v in raw["packs"].items()}
    recipes = {r["name"]: Recipe(r["name"], r["serves"], r["items"]) for r in raw["recipes"]}
    return packs, recipes


def scale(recipe: Recipe, people: int) -> dict[str, float]:
    if people < 1:
        raise CookError("people must be at least 1")
    f = people / recipe.serves
    return {k: round(v * f, 2) for k, v in recipe.items.items()}


def combine(scaled: list[dict[str, float]]) -> dict[str, float]:
    total: dict[str, float] = {}
    for s in scaled:
        for k, v in s.items():
            total[k] = round(total.get(k, 0) + v, 2)
    return total


def shopping_list(
    needs: dict[str, float], packs: dict[str, Pack], on_hand: dict[str, float] | None = None
) -> list[Line]:
    """Round each need up to whole packs after subtracting what is already in the cupboard."""
    on_hand = on_hand or {}
    lines = []
    for item, need in sorted(needs.items()):
        if item not in packs:
            raise CookError(f"no pack size for {item}")
        short = max(need - on_hand.get(item, 0), 0)
        p = packs[item]
        n = math.ceil(short / p.size - 1e-9) if short else 0
        lines.append(Line(item, need, p.unit, n, round(n * p.price, 2), round(n * p.size - short, 2) if n else 0.0))
    return lines


def total(lines: list[Line]) -> float:
    return round(sum(x.cost for x in lines), 2)


def waste_value(lines: list[Line], packs: dict[str, Pack]) -> float:
    """Money spent on packs' unused leftovers."""
    return round(sum(x.leftover / packs[x.item].size * packs[x.item].price for x in lines), 2)


def shared_vs_separate(recipes: list[Recipe], people: int, packs: dict[str, Pack]) -> tuple[float, float]:
    """(one combined shop, shopping for each recipe separately): combining shares part-used packs."""
    scaled = [scale(r, people) for r in recipes]
    combined = total(shopping_list(combine(scaled), packs))
    separate = round(sum(total(shopping_list(s, packs)) for s in scaled), 2)
    return combined, separate
