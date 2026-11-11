"""Make change with the fewest coins from a till with limited stock (bounded coin-change DP)."""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "till.json"


class ChangeError(ValueError):
    """Invalid till or amount."""


def build(till: dict[str, int], amount: int) -> dict[int, int]:
    out = {int(k): int(v) for k, v in till.items()}
    if not out or any(k < 1 or v < 0 for k, v in out.items()) or not 0 <= amount <= 10000:
        raise ChangeError("till needs positive coin values, non-negative stock and an amount of 0-10000")
    return out


def fewest_coins(till: dict[int, int], amount: int) -> dict[int, int] | None:
    """Fewest-coin change for `amount` within the stock, or None if impossible."""
    inf = 10**9
    best = [inf] * (amount + 1)
    best[0] = 0
    used: list[dict[int, int]] = [{} for _ in range(amount + 1)]
    for coin, stock in till.items():
        for _ in range(stock):  # 0/1 expansion: each physical coin is one item
            for t in range(amount, coin - 1, -1):
                if best[t - coin] + 1 < best[t]:
                    best[t] = best[t - coin] + 1
                    used[t] = {**used[t - coin], coin: used[t - coin].get(coin, 0) + 1}
    return dict(sorted(used[amount].items(), reverse=True)) if best[amount] < inf else None


def greedy(till: dict[int, int], amount: int) -> dict[int, int] | None:
    """Baseline: always hand over the biggest coin that fits and is in stock."""
    left, out = amount, {}
    for coin in sorted(till, reverse=True):
        n = min(left // coin, till[coin])
        if n:
            out[coin] = n
            left -= n * coin
    return out if left == 0 else None


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
