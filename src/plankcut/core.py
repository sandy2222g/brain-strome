"""Cut a plank into pieces to maximise sale value (rod-cutting DP), with a single-size baseline."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "prices.json"


class PlankError(ValueError):
    """Invalid plank length or price list."""


def build(prices: dict[str, float], length: int) -> dict[int, float]:
    out = {int(k): float(v) for k, v in prices.items()}
    if not out or any(k < 1 or v <= 0 for k, v in out.items()) or not 1 <= length <= 1000:
        raise PlankError("prices need positive lengths and values; plank length 1-1000 cm")
    return out


def best_cuts(prices: dict[int, float], length: int) -> tuple[float, list[int]]:
    """Maximum value and the pieces (longest first); leftover offcut is worth nothing."""
    value = [0.0] * (length + 1)
    choice = [0] * (length + 1)
    for n in range(1, length + 1):
        value[n], choice[n] = value[n - 1], 0  # 0 = waste 1 cm
        for size, price in prices.items():
            if size <= n and value[n - size] + price > value[n] + 1e-9:
                value[n], choice[n] = value[n - size] + price, size
    pieces, n = [], length
    while n > 0:
        if choice[n] == 0:
            n -= 1
        else:
            pieces.append(choice[n])
            n -= choice[n]
    return round(value[length], 2), sorted(pieces, reverse=True)


def single_size(prices: dict[int, float], length: int) -> tuple[float, list[int]]:
    """Baseline: cut only the size with the best price per cm, as many as fit."""
    size = max(prices, key=lambda s: prices[s] / s)
    n = length // size
    return round(n * prices[size], 2), [size] * n


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
