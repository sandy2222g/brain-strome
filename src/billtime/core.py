"""Daily balance simulation and the cheapest fix: move a bill to a later day."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "month.json"


class BillError(ValueError):
    """Raised for invalid money data."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _check(items: list[dict[str, Any]], days: int) -> None:
    for it in items:
        if not 1 <= int(it["day"]) <= days or float(it["amount"]) < 0:
            raise BillError(f"bad entry {it['name']!r}")


def balances(month: dict[str, Any], moves: dict[str, int] | None = None) -> list[float]:
    """End-of-day balance for each day; `moves` maps 'name@day' to a new day for that bill."""
    days = int(month["days"])
    if days < 1:
        raise BillError("days must be positive")
    _check(month["income"], days)
    _check(month["bills"], days)
    delta = [0.0] * (days + 1)
    for inc in month["income"]:
        delta[int(inc["day"])] += float(inc["amount"])
    for b in month["bills"]:
        day = (moves or {}).get(f"{b['name']}@{b['day']}", int(b["day"]))
        if not 1 <= day <= days:
            raise BillError("moved day out of range")
        delta[day] -= float(b["amount"])
    bal, out = float(month["opening_balance"]), []
    for d in range(1, days + 1):
        bal += delta[d]
        out.append(round(bal, 2))
    return out


def shortfalls(series: list[float]) -> list[dict[str, Any]]:
    """Days where the balance is below zero, with the amount."""
    return [{"day": i + 1, "balance": b} for i, b in enumerate(series) if b < 0]


def suggest_moves(month: dict[str, Any], max_shift: int = 7) -> dict[str, Any]:
    """Greedy fix: for the first overdrawn day, delay the largest bill due on or before it to the next payday."""
    moves: dict[str, int] = {}
    series = balances(month, moves)
    for _ in range(len(month["bills"])):
        bad = shortfalls(series)
        if not bad:
            break
        first = bad[0]["day"]
        paydays = sorted(int(i["day"]) for i in month["income"])
        later = [p for p in paydays if p > first]
        if not later:
            break
        target = later[0]
        candidates = [
            b for b in month["bills"]
            if f"{b['name']}@{b['day']}" not in moves and int(b["day"]) <= first and target - int(b["day"]) <= max_shift
        ]
        if not candidates:
            break
        pick = max(candidates, key=lambda b: (float(b["amount"]), b["name"]))
        moves[f"{pick['name']}@{pick['day']}"] = target
        series = balances(month, moves)
    return {"moves": moves, "balances": series, "shortfalls": shortfalls(series)}
