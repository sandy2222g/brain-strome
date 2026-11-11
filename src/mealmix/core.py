"""Pick daily servings of foods that meet calorie and protein targets at the lowest cost.

The classic diet problem, solved exactly by trying every combination of 0..max_servings of each food
(at most 5^9 about 2 million, pruned by cost). The baseline is the usual shortcut: buy the cheapest food per
calorie until the calories are met, which ignores protein.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "foods.json"
MAX_FOODS = 9


class MixError(ValueError):
    """Invalid input or no feasible mix."""


@dataclass(frozen=True)
class Food:
    name: str
    cost: float
    kcal: int
    protein: int


@dataclass(frozen=True)
class Targets:
    kcal_min: int
    kcal_max: int
    protein_min: int


def build(foods: list[Food], targets: Targets, max_servings: int) -> tuple[list[Food], Targets, int]:
    if not 1 <= len(foods) <= MAX_FOODS:
        raise MixError(f"between 1 and {MAX_FOODS} foods")
    if not 1 <= max_servings <= 8:
        raise MixError("max servings must be between 1 and 8")
    if targets.kcal_min <= 0 or targets.kcal_max < targets.kcal_min or targets.protein_min < 0:
        raise MixError("bad targets")
    if len({f.name for f in foods}) != len(foods) or any(f.cost <= 0 or f.kcal <= 0 or f.protein < 0 for f in foods):
        raise MixError("foods need unique names, positive cost and calories")
    return foods, targets, max_servings


def load(path: Path = DATA) -> tuple[list[Food], Targets, int]:
    raw = json.loads(path.read_text())
    return build([Food(**f) for f in raw["foods"]], Targets(**raw["targets"]), raw["max_servings"])


def totals(foods: list[Food], servings: list[int]) -> tuple[float, int, int]:
    return (
        round(sum(f.cost * s for f, s in zip(foods, servings, strict=True)), 2),
        sum(f.kcal * s for f, s in zip(foods, servings, strict=True)),
        sum(f.protein * s for f, s in zip(foods, servings, strict=True)),
    )


def meets(foods: list[Food], targets: Targets, servings: list[int]) -> bool:
    _, kcal, protein = totals(foods, servings)
    return targets.kcal_min <= kcal <= targets.kcal_max and protein >= targets.protein_min


def cheapest_per_kcal(foods: list[Food], targets: Targets, max_servings: int) -> list[int]:
    """Baseline: fill calories with the cheapest-per-calorie food first, ignoring protein."""
    servings = [0] * len(foods)
    kcal = 0
    for i in sorted(range(len(foods)), key=lambda i: foods[i].cost / foods[i].kcal):
        while servings[i] < max_servings and kcal + foods[i].kcal <= targets.kcal_max and kcal < targets.kcal_min:
            servings[i] += 1
            kcal += foods[i].kcal
    return servings


def best_mix(foods: list[Food], targets: Targets, max_servings: int) -> list[int]:
    best: list[int] | None = None
    best_cost = float("inf")
    cur = [0] * len(foods)

    def go(i: int, cost: float, kcal: int, protein: int) -> None:
        nonlocal best, best_cost
        if cost >= best_cost or kcal > targets.kcal_max:
            return
        if i == len(foods):
            if kcal >= targets.kcal_min and protein >= targets.protein_min:
                best, best_cost = list(cur), cost
            return
        f = foods[i]
        for s in range(max_servings + 1):
            cur[i] = s
            go(i + 1, cost + f.cost * s, kcal + f.kcal * s, protein + f.protein * s)
        cur[i] = 0

    go(0, 0.0, 0, 0)
    if best is None:
        raise MixError("no mix of these foods meets the targets")
    return best
