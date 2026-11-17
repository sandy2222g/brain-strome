"""Group swimmers into lanes of similar speed (invented data)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "swimmers.json"


class LaneError(ValueError):
    """Raised for impossible or invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def _swimmers(raw: list[dict[str, Any]]) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for s in raw:
        t = float(s["time100"])
        if t <= 0:
            raise LaneError("100 m times must be positive")
        out.append((str(s["name"]), t))
    return out


def _lane(members: list[tuple[str, float]]) -> dict[str, Any]:
    times = [t for _, t in members]
    return {
        "swimmers": [n for n, _ in members],
        "fastest": min(times),
        "slowest": max(times),
        "spread": round(max(times) - min(times), 1),
    }


def _result(groups: list[list[tuple[str, float]]]) -> dict[str, Any]:
    lanes = [_lane(g) for g in groups]
    return {"lanes": lanes, "total_spread": round(sum(x["spread"] for x in lanes), 1),
            "worst_spread": max(x["spread"] for x in lanes)}


def _check(n: int, lanes: int, capacity: int) -> None:
    if lanes < 1 or capacity < 1:
        raise LaneError("lanes and capacity must be at least 1")
    if n == 0:
        raise LaneError("no swimmers")
    if n > lanes * capacity:
        raise LaneError("not enough lane space for all swimmers")


def assign(raw: list[dict[str, Any]], lanes: int, capacity: int) -> dict[str, Any]:
    """Split the speed-sorted swimmers into contiguous lanes, minimising the summed time spread.

    Dynamic programme over (swimmers placed, lanes used); every used lane holds 1..capacity swimmers.
    """
    sw = sorted(_swimmers(raw), key=lambda x: x[1])
    n = len(sw)
    _check(n, lanes, capacity)
    k = min(lanes, n)
    inf = math.inf
    cost = [[inf] * (k + 1) for _ in range(n + 1)]
    cut = [[0] * (k + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    for j in range(1, k + 1):
        for i in range(j, n + 1):
            for p in range(max(j - 1, i - capacity), i):
                if cost[p][j - 1] == inf:
                    continue
                c = cost[p][j - 1] + (sw[i - 1][1] - sw[p][1])
                if c < cost[i][j] - 1e-12:
                    cost[i][j], cut[i][j] = c, p
    if cost[n][k] == inf:
        raise LaneError("cannot fit swimmers into the lanes")
    groups: list[list[tuple[str, float]]] = []
    i = n
    for j in range(k, 0, -1):
        p = cut[i][j]
        groups.append(sw[p:i])
        i = p
    groups.reverse()
    return _result(groups)


def signup_order(raw: list[dict[str, Any]], lanes: int, capacity: int) -> dict[str, Any]:
    """Baseline: fill lanes in sign-up order with equal-sized groups."""
    sw = _swimmers(raw)
    n = len(sw)
    _check(n, lanes, capacity)
    k = min(lanes, n)
    size = math.ceil(n / k)
    groups = [sw[i : i + size] for i in range(0, n, size)]
    return _result([g for g in groups if g])


def compare(raw: list[dict[str, Any]], lanes: int, capacity: int) -> dict[str, Any]:
    a, b = assign(raw, lanes, capacity), signup_order(raw, lanes, capacity)
    return {"assigned": a, "signup_order": b, "spread_saved": round(b["total_spread"] - a["total_spread"], 1)}
