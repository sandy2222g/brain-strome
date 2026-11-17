"""Month-by-month payoff simulation in integer cents for avalanche, snowball and minimum-only plans."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "debts.json"
MAX_MONTHS = 600


class DebtError(ValueError):
    """Raised for invalid debts, or a budget that can never clear them."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def cents(x: float) -> int:
    return round(float(x) * 100)


def _debts(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw:
        raise DebtError("need at least one debt")
    out = []
    for d in raw:
        bal, apr, mini = cents(d["balance"]), float(d["apr"]), cents(d["minimum"])
        if bal <= 0 or apr < 0 or mini <= 0:
            raise DebtError(f"bad numbers for {d['name']!r}")
        out.append({"name": str(d["name"]), "bal": bal, "apr": apr, "min": mini})
    if len({d["name"] for d in out}) != len(out):
        raise DebtError("debt names must be unique")
    return out


def _target_key(strategy: str | list[str]) -> Callable[[dict[str, Any]], tuple[Any, ...]]:
    if isinstance(strategy, list):  # an explicit payoff priority, used to test the named strategies
        return lambda d: (strategy.index(d["name"]),)
    if strategy == "avalanche":
        return lambda d: (-d["apr"], d["bal"], d["name"])
    if strategy == "snowball":
        return lambda d: (d["bal"], -d["apr"], d["name"])
    raise DebtError(f"unknown strategy {strategy!r}")


def simulate(raw: list[dict[str, Any]], budget: float, strategy: str | list[str]) -> dict[str, Any]:
    """Pay all minimums, put every spare cent on the target debt; freed minimums roll into the budget.

    `minimum_only` pays only the minimums and never rolls payments over; a list of names is a custom priority.
    """
    debts = _debts(raw)
    total_budget = cents(budget)
    if strategy != "minimum_only":
        key = _target_key(strategy)
        if total_budget < sum(d["min"] for d in debts):
            raise DebtError("budget is below the sum of the minimum payments")
    interest_total, month, series = 0, 0, [sum(d["bal"] for d in debts)]
    order: list[str] = []
    while any(d["bal"] > 0 for d in debts):
        month += 1
        if month > MAX_MONTHS:
            raise DebtError("debts are not cleared within 50 years at this budget")
        for d in debts:
            if d["bal"] > 0:
                add = round(d["bal"] * d["apr"] / 1200)
                d["bal"] += add
                interest_total += add
        spare = total_budget if strategy != "minimum_only" else 0
        for d in debts:
            if d["bal"] > 0:
                pay = min(d["min"], d["bal"])
                d["bal"] -= pay
                spare -= pay if strategy != "minimum_only" else 0
        if strategy != "minimum_only":
            for d in sorted((x for x in debts if x["bal"] > 0), key=key):
                pay = min(spare, d["bal"])
                d["bal"] -= pay
                spare -= pay
                if spare <= 0:
                    break
        for d in debts:
            if d["bal"] == 0 and d["name"] not in order:
                order.append(d["name"])
        series.append(sum(d["bal"] for d in debts))
    return {
        "strategy": strategy if isinstance(strategy, str) else "custom",
        "months": month,
        "interest": interest_total / 100,
        "paid_off_order": order,
        "balances": [round(x / 100, 2) for x in series],
    }


def compare(raw: list[dict[str, Any]], budget: float) -> dict[str, Any]:
    plans = {s: simulate(raw, budget, s) for s in ("avalanche", "snowball", "minimum_only")}
    return {
        "plans": plans,
        "interest_saved_vs_snowball": round(plans["snowball"]["interest"] - plans["avalanche"]["interest"], 2),
        "interest_saved_vs_minimum": round(plans["minimum_only"]["interest"] - plans["avalanche"]["interest"], 2),
    }
