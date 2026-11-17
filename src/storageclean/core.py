"""Choose which items to delete to free a target amount of space while losing the least value (invented files)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "files.json"


class CleanError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def _items(raw: list[dict[str, Any]], target: int) -> list[tuple[str, int, int]]:
    if target <= 0:
        raise CleanError("target must be positive")
    out = []
    for r in raw:
        mb, keep = int(r["mb"]), int(r["keep"])
        if mb <= 0 or keep < 0:
            raise CleanError(f"bad size or keep score for {r['name']}")
        out.append((str(r["name"]), mb, keep))
    if sum(mb for _, mb, _ in out) < target:
        raise CleanError("even deleting everything would not free that much")
    return out


def _result(items: list[tuple[str, int, int]], chosen: list[int]) -> dict[str, Any]:
    picked = [items[i] for i in sorted(chosen)]
    return {
        "delete": [{"name": n, "mb": mb, "keep": k} for n, mb, k in picked],
        "freed_mb": sum(mb for _, mb, _ in picked),
        "value_lost": sum(k for _, _, k in picked),
    }


def optimal(raw: list[dict[str, Any]], target: int) -> dict[str, Any]:
    """0/1 knapsack in reverse: least total keep-value among subsets freeing at least `target` MB.

    dp[f] = least value lost to free f MB (freed amounts above the target are capped at the target).
    """
    items = _items(raw, target)
    inf = float("inf")
    dp = [0.0] + [inf] * target
    take: list[list[int | None]] = []
    for _, mb, keep in items:
        new = dp[:]
        prev: list[int | None] = [None] * (target + 1)
        for f in range(target + 1):
            if dp[f] == inf:
                continue
            g = min(target, f + mb)
            if dp[f] + keep < new[g]:
                new[g], prev[g] = dp[f] + keep, f
        take.append(prev)
        dp = new
    chosen: list[int] = []
    f = target
    for i in range(len(items) - 1, -1, -1):
        p = take[i][f]
        if p is not None:
            chosen.append(i)
            f = p
    return _result(items, chosen)


def biggest_first(raw: list[dict[str, Any]], target: int) -> dict[str, Any]:
    """Baseline: delete the largest items until enough space is free."""
    items = _items(raw, target)
    order = sorted(range(len(items)), key=lambda i: -items[i][1])
    chosen, freed = [], 0
    for i in order:
        if freed >= target:
            break
        chosen.append(i)
        freed += items[i][1]
    return _result(items, chosen)


def compare(raw: list[dict[str, Any]], target: int) -> dict[str, Any]:
    o, b = optimal(raw, target), biggest_first(raw, target)
    return {"optimal": o, "biggest_first": b, "value_saved": b["value_lost"] - o["value_lost"]}
