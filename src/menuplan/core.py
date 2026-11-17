"""Backtracking search for a week of dinners under simple rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "dishes.json"
WEEKEND = {"Sat", "Sun"}


class MenuError(ValueError):
    """Raised for invalid input or when no plan exists."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _allowed(dish: dict[str, Any], day: str, used: list[dict[str, Any]], weeknight_max: int) -> bool:
    if dish in used:
        return False
    if day not in WEEKEND and dish["minutes"] > weeknight_max:
        return False
    return not used or used[-1]["protein"] != dish["protein"]


def plan(dishes: list[dict[str, Any]], days: list[str], weeknight_max: int = 30) -> list[dict[str, Any]]:
    """Assign one dish per day: no repeat dish, no same protein on consecutive days, quick dishes on weeknights.

    Dishes are tried in name order, so the result is deterministic. Raises if no plan exists.
    """
    if not days:
        raise MenuError("need at least one day")
    if len(dishes) < len(days):
        raise MenuError("not enough dishes for the days")
    ordered = sorted(dishes, key=lambda d: d["name"])
    chosen: list[dict[str, Any]] = []

    def go(i: int) -> bool:
        if i == len(days):
            return True
        for d in ordered:
            if _allowed(d, days[i], chosen, weeknight_max):
                chosen.append(d)
                if go(i + 1):
                    return True
                chosen.pop()
        return False

    if not go(0):
        raise MenuError("no plan satisfies the rules")
    return [{"day": day, **d} for day, d in zip(days, chosen, strict=True)]


def violations(rows: list[dict[str, Any]], weeknight_max: int = 30) -> list[str]:
    """Rule breaks in a given plan (used to show why a list-order plan fails)."""
    out = []
    for i, r in enumerate(rows):
        if r["day"] not in WEEKEND and r["minutes"] > weeknight_max:
            out.append(f"{r['day']}: {r['name']} takes {r['minutes']} min")
        if i and rows[i - 1]["protein"] == r["protein"]:
            out.append(f"{r['day']}: {r['protein']} two days running")
    names = [r["name"] for r in rows]
    out += [f"{n} repeated" for n in sorted(set(names)) if names.count(n) > 1]
    return out


def list_order_plan(dishes: list[dict[str, Any]], days: list[str]) -> list[dict[str, Any]]:
    """Baseline: just take the first dishes in the order listed."""
    return [{"day": day, **d} for day, d in zip(days, dishes, strict=False)]
