"""Shortest walking route through a supermarket.

Layout: parallel aisles joined by a front corridor (depth 0) and a back corridor (depth `depth`).
You enter at the front of aisle 0 and finish at the checkout at the front of the last aisle. Walking
distance between two shelf positions follows the aisles (no cutting through shelves). The best visiting
order is found exactly with Held-Karp dynamic programming (<= 14 items) and by nearest-neighbour +
2-opt for larger lists.
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "store.json"
EXACT_LIMIT = 14


class RouteError(ValueError):
    """Invalid request."""


@dataclass(frozen=True)
class Store:
    aisles: int
    depth: int
    aisle_gap: int
    names: list[str]
    items: dict[str, tuple[int, int]]

    @property
    def entrance(self) -> tuple[int, int]:
        return (0, 0)

    @property
    def checkout(self) -> tuple[int, int]:
        return (self.aisles - 1, 0)


def load(path: Path = DATA) -> Store:
    raw = json.loads(path.read_text())
    return Store(
        raw["aisles"],
        raw["depth"],
        raw["aisle_gap"],
        raw["aisle_names"],
        {k: tuple(v) for k, v in raw["items"].items()},
    )


def dist(store: Store, a: tuple[int, int], b: tuple[int, int]) -> int:
    (a1, d1), (a2, d2) = a, b
    if a1 == a2:
        return abs(d1 - d2)
    across = abs(a1 - a2) * store.aisle_gap
    front = d1 + across + d2
    back = (store.depth - d1) + across + (store.depth - d2)
    return min(front, back)


def route_length(store: Store, order: list[str]) -> int:
    pts = [store.entrance, *[store.items[i] for i in order], store.checkout]
    return sum(dist(store, p, q) for p, q in zip(pts, pts[1:], strict=False))


def check_items(store: Store, items: list[str]) -> list[str]:
    if not items:
        raise RouteError("shopping list is empty")
    unknown = [i for i in items if i not in store.items]
    if unknown:
        raise RouteError(f"not sold here: {', '.join(unknown)}")
    return list(dict.fromkeys(items))


def exact_order(store: Store, items: list[str]) -> list[str]:
    """Held-Karp: O(n^2 * 2^n) shortest path from entrance through all items to checkout."""
    n = len(items)
    pts = [store.items[i] for i in items]
    d = [[dist(store, pts[i], pts[j]) for j in range(n)] for i in range(n)]
    start = [dist(store, store.entrance, pts[i]) for i in range(n)]
    end = [dist(store, pts[i], store.checkout) for i in range(n)]
    inf = float("inf")
    best = [[inf] * n for _ in range(1 << n)]
    prev = [[-1] * n for _ in range(1 << n)]
    for i in range(n):
        best[1 << i][i] = start[i]
    for mask in range(1 << n):
        for last in range(n):
            cur = best[mask][last]
            if cur == inf or not mask >> last & 1:
                continue
            for nxt in range(n):
                if mask >> nxt & 1:
                    continue
                m2 = mask | 1 << nxt
                c = cur + d[last][nxt]
                if c < best[m2][nxt]:
                    best[m2][nxt], prev[m2][nxt] = c, last
    full = (1 << n) - 1
    last = min(range(n), key=lambda i: best[full][i] + end[i])
    order, mask = [], full
    while last != -1:
        order.append(items[last])
        mask, last = mask ^ (1 << last), prev[mask][last]
    return order[::-1]


def heuristic_order(store: Store, items: list[str]) -> list[str]:
    """Nearest neighbour then 2-opt improvement (used above EXACT_LIMIT items)."""
    left, cur, order = list(items), store.entrance, []
    while left:
        nxt = min(left, key=lambda i: (dist(store, cur, store.items[i]), i))
        order.append(nxt)
        left.remove(nxt)
        cur = store.items[nxt]
    improved = True
    while improved:
        improved = False
        for i, j in itertools.combinations(range(len(order)), 2):
            cand = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
            if route_length(store, cand) < route_length(store, order):
                order, improved = cand, True
    return order


def best_route(store: Store, items: list[str]) -> list[str]:
    items = check_items(store, items)
    return exact_order(store, items) if len(items) <= EXACT_LIMIT else heuristic_order(store, items)


def list_order_route(store: Store, items: list[str]) -> list[str]:
    """Baseline: walk the list in the order it was written."""
    return check_items(store, items)


def steps(store: Store, order: list[str]) -> list[dict[str, object]]:
    pts = [("Entrance", store.entrance), *[(i, store.items[i]) for i in order], ("Checkout", store.checkout)]
    out, total = [], 0
    for (_, p), (name, q) in zip(pts, pts[1:], strict=False):
        d = dist(store, p, q)
        total += d
        out.append(
            {"item": name, "aisle": q[0], "aisle_name": store.names[q[0]], "depth": q[1], "leg": d, "total": total}
        )
    return out
