"""Pack household items into moving boxes: two limits per box (weight and volume), as few boxes as possible.

This is two-dimensional vector bin packing. `next_fit` is what people do by hand (fill a box, start the next),
`first_fit_decreasing` is the standard heuristic, and `optimal` is an exact branch and bound for small moves.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "items.json"
MAX_EXACT_ITEMS = 24


class PackError(ValueError):
    """Invalid input."""


@dataclass(frozen=True)
class Item:
    name: str
    kg: float
    litres: float


@dataclass(frozen=True)
class Box:
    items: tuple[Item, ...]

    @property
    def kg(self) -> float:
        return round(sum(i.kg for i in self.items), 3)

    @property
    def litres(self) -> float:
        return round(sum(i.litres for i in self.items), 3)


def load(path: Path = DATA) -> tuple[float, float, list[Item]]:
    raw = json.loads(path.read_text())
    return raw["box_kg"], raw["box_litres"], [Item(i["name"], i["kg"], i["litres"]) for i in raw["items"]]


def validate(box_kg: float, box_litres: float, items: list[Item]) -> None:
    if box_kg <= 0 or box_litres <= 0:
        raise PackError("box limits must be positive")
    if not items:
        raise PackError("nothing to pack")
    for i in items:
        if i.kg <= 0 or i.litres <= 0:
            raise PackError(f"'{i.name}' needs a positive weight and volume")
        if i.kg > box_kg or i.litres > box_litres:
            raise PackError(f"'{i.name}' does not fit in an empty box")


def _fits(used: tuple[float, float], item: Item, box_kg: float, box_litres: float) -> bool:
    return used[0] + item.kg <= box_kg + 1e-9 and used[1] + item.litres <= box_litres + 1e-9


def next_fit(box_kg: float, box_litres: float, items: list[Item]) -> list[Box]:
    """Baseline: go through the list in order, close a box as soon as the next item does not fit."""
    validate(box_kg, box_litres, items)
    boxes: list[list[Item]] = [[]]
    used = (0.0, 0.0)
    for it in items:
        if not _fits(used, it, box_kg, box_litres):
            boxes.append([])
            used = (0.0, 0.0)
        boxes[-1].append(it)
        used = (used[0] + it.kg, used[1] + it.litres)
    return [Box(tuple(b)) for b in boxes]


def _size_key(box_kg: float, box_litres: float) -> Callable[[Item], float]:
    return lambda it: -max(it.kg / box_kg, it.litres / box_litres)


def first_fit_decreasing(box_kg: float, box_litres: float, items: list[Item]) -> list[Box]:
    """Largest item first (by its tighter limit), each into the first box with room."""
    validate(box_kg, box_litres, items)
    boxes: list[list[Item]] = []
    used: list[tuple[float, float]] = []
    for it in sorted(items, key=_size_key(box_kg, box_litres)):
        for k, u in enumerate(used):
            if _fits(u, it, box_kg, box_litres):
                boxes[k].append(it)
                used[k] = (u[0] + it.kg, u[1] + it.litres)
                break
        else:
            boxes.append([it])
            used.append((it.kg, it.litres))
    return [Box(tuple(b)) for b in boxes]


def lower_bound(box_kg: float, box_litres: float, items: list[Item]) -> int:
    """No packing can use fewer boxes than the total weight or volume demands."""
    return max(
        math.ceil(sum(i.kg for i in items) / box_kg - 1e-9),
        math.ceil(sum(i.litres for i in items) / box_litres - 1e-9),
    )


def optimal(box_kg: float, box_litres: float, items: list[Item], node_limit: int = 400_000) -> tuple[list[Box], bool]:
    """Exact minimum number of boxes by branch and bound. Returns (boxes, proved_optimal).

    Items go in largest first; each is tried in every open box (skipping boxes with identical contents)
    and in a new box. If `node_limit` is hit the best packing so far is returned with proved_optimal False.
    """
    validate(box_kg, box_litres, items)
    if len(items) > MAX_EXACT_ITEMS:
        raise PackError(f"exact search is limited to {MAX_EXACT_ITEMS} items")
    order = sorted(items, key=_size_key(box_kg, box_litres))
    best = first_fit_decreasing(box_kg, box_litres, items)
    lb = lower_bound(box_kg, box_litres, items)
    best_boxes = [list(b.items) for b in best]
    state = {"nodes": 0, "best": len(best_boxes), "cut": False}
    cur: list[list[Item]] = []
    used: list[tuple[float, float]] = []

    def go(idx: int) -> None:
        if state["best"] <= lb or state["cut"]:
            return
        state["nodes"] += 1
        if state["nodes"] > node_limit:
            state["cut"] = True
            return
        if idx == len(order):
            if len(cur) < state["best"]:
                state["best"] = len(cur)
                best_boxes[:] = [list(b) for b in cur]
            return
        it = order[idx]
        seen: set[tuple[float, float]] = set()
        for k in range(len(cur)):
            u = used[k]
            if u in seen or not _fits(u, it, box_kg, box_litres):
                continue
            seen.add(u)
            cur[k].append(it)
            used[k] = (u[0] + it.kg, u[1] + it.litres)
            go(idx + 1)
            cur[k].pop()
            used[k] = u
        if len(cur) + 1 < state["best"]:
            cur.append([it])
            used.append((it.kg, it.litres))
            go(idx + 1)
            cur.pop()
            used.pop()

    go(0)
    return [Box(tuple(b)) for b in best_boxes], not state["cut"]
