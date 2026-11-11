"""Spend a fixed gift budget across several people to maximise total joy.

Each person has candidate gifts (whole-dollar price, joy score 1-10); at most one gift per person.
A multiple-choice knapsack DP over the budget finds the best total joy exactly.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "gifts.json"
MAX_PEOPLE = 20


class GiftError(ValueError):
    """Invalid budget or gift list."""


@dataclass(frozen=True)
class Gift:
    name: str
    price: int
    joy: int


def build(people: dict[str, list[dict]], budget: int) -> dict[str, list[Gift]]:  # type: ignore[type-arg]
    if not 1 <= len(people) <= MAX_PEOPLE or not 1 <= budget <= 2000:
        raise GiftError("1-20 people and a budget of 1-2000")
    out: dict[str, list[Gift]] = {}
    for person, gifts in people.items():
        out[person] = [Gift(str(g["name"]), int(g["price"]), int(g["joy"])) for g in gifts]
        if not out[person] or any(g.price < 1 or not 1 <= g.joy <= 10 for g in out[person]):
            raise GiftError(f"{person}: need gifts with price >= 1 and joy 1-10")
    return out


def best_plan(people: dict[str, list[Gift]], budget: int) -> tuple[int, int, dict[str, Gift | None]]:
    """Return (total joy, total spent, chosen gift per person) with the maximum joy within budget."""
    names = list(people)
    dp = [[0] * (budget + 1) for _ in range(len(names) + 1)]
    for i, n in enumerate(names, 1):
        for b in range(budget + 1):
            best = dp[i - 1][b]
            for g in people[n]:
                if g.price <= b:
                    best = max(best, dp[i - 1][b - g.price] + g.joy)
            dp[i][b] = best
    chosen: dict[str, Gift | None] = {}
    b = budget
    for i in range(len(names), 0, -1):
        pick = None
        if dp[i][b] != dp[i - 1][b]:
            pick = next(g for g in people[names[i - 1]] if g.price <= b and dp[i - 1][b - g.price] + g.joy == dp[i][b])
            b -= pick.price
        chosen[names[i - 1]] = pick
    chosen = {n: chosen[n] for n in names}
    return dp[-1][budget], sum(g.price for g in chosen.values() if g), chosen


def equal_share_plan(people: dict[str, list[Gift]], budget: int) -> tuple[int, int, dict[str, Gift | None]]:
    """Baseline: give everyone the same allowance and let them pick the best gift within it."""
    share = budget // len(people)
    chosen: dict[str, Gift | None] = {}
    for n, gifts in people.items():
        ok = [g for g in gifts if g.price <= share]
        chosen[n] = max(ok, key=lambda g: g.joy) if ok else None
    return sum(g.joy for g in chosen.values() if g), sum(g.price for g in chosen.values() if g), chosen


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
