"""Cheapest pizza order that gives every guest their slices within their diet (invented menu)."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "party.json"
DIETS = ("vegan", "vegetarian", "meat")  # strictest first; a guest can eat pizzas of their own diet or stricter
MAX_PER_PIZZA = 12


class PizzaError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def _clean(people: dict[str, int], menu: list[dict[str, Any]], each: int) -> list[dict[str, Any]]:
    if each < 1:
        raise PizzaError("slices per person must be at least 1")
    if any(d not in DIETS for d in people) or any(v < 0 for v in people.values()) or not sum(people.values()):
        raise PizzaError("people needs non-negative counts for vegan, vegetarian, meat and at least one guest")
    out = []
    for m in menu:
        if m["diet"] not in DIETS or m["slices"] < 1 or m["price"] < 0:
            raise PizzaError("bad menu item: " + str(m.get("name")))
        out.append({"name": m["name"], "cents": round(m["price"] * 100), "slices": int(m["slices"]), "diet": m["diet"]})
    for diet in DIETS:
        if people.get(diet, 0) and not any(DIETS.index(m["diet"]) <= DIETS.index(diet) for m in out):
            raise PizzaError(f"no pizza on the menu suits {diet} guests")
    return out


def feeds(counts: list[int], menu: list[dict[str, Any]], people: dict[str, int], each: int, meat_pct: int = 0) -> bool:
    """Exact check: guest groups are nested by diet, so Hall's condition on three prefixes is enough.

    `meat_pct` also requires that share of the meat eaters' slices to be actual meat pizza.
    """
    supply = dict.fromkeys(DIETS, 0)
    for n, m in zip(counts, menu, strict=True):
        supply[m["diet"]] += n * m["slices"]
    need = {d: people.get(d, 0) * each for d in DIETS}
    return (
        supply["meat"] * 100 >= meat_pct * need["meat"]
        and need["vegan"] <= supply["vegan"]
        and need["vegan"] + need["vegetarian"] <= supply["vegan"] + supply["vegetarian"]
        and sum(need.values()) <= sum(supply.values())
    )


def _plan(counts: list[int], menu: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = list(zip(counts, menu, strict=True))
    lines = [{"name": m["name"], "count": n, "cost": n * m["cents"] / 100} for n, m in pairs if n]
    return {"lines": lines, "pizzas": sum(counts), "total": sum(n * m["cents"] for n, m in pairs) / 100}


def cheapest(people: dict[str, int], menu_raw: list[dict[str, Any]], each: int, meat_pct: int = 0) -> dict[str, Any]:
    """Enumerate pizza counts per menu item and keep the cheapest order that feeds everyone."""
    menu = _clean(people, menu_raw, each)
    total_need = sum(people.values()) * each
    limit = min(MAX_PER_PIZZA, max(1, -(-total_need // min(m["slices"] for m in menu))))
    best: tuple[int, int, list[int]] | None = None
    for counts in itertools.product(range(limit + 1), repeat=len(menu)):
        if not feeds(list(counts), menu, people, each, meat_pct):
            continue
        cost = sum(n * m["cents"] for n, m in zip(counts, menu, strict=True))
        key = (cost, sum(counts), list(counts))
        if best is None or key < best:
            best = key
    if best is None:
        raise PizzaError("no order within the size limit feeds everyone")
    plan = _plan(best[2], menu)
    plan["spare_slices"] = sum(n * m["slices"] for n, m in zip(best[2], menu, strict=True)) - total_need
    return plan


def cheapest_slice_only(people: dict[str, int], menu_raw: list[dict[str, Any]], each: int) -> dict[str, Any]:
    """Baseline: ignore diets, buy only the cheapest-per-slice pizza until the slice count is covered."""
    menu = _clean(people, menu_raw, each)
    pick = min(range(len(menu)), key=lambda i: (menu[i]["cents"] / menu[i]["slices"], i))
    need = sum(people.values()) * each
    n = -(-need // menu[pick]["slices"])
    counts = [n if i == pick else 0 for i in range(len(menu))]
    plan = _plan(counts, menu)
    unfed = 0
    if not feeds(counts, menu, people, each):
        # guests of diets the pizza does not suit go hungry
        suits = DIETS.index(menu[pick]["diet"])
        unfed = sum(c for d, c in people.items() if DIETS.index(d) < suits)
    plan["unfed_guests"] = unfed
    return plan


def compare(people: dict[str, int], menu: list[dict[str, Any]], each: int, meat_pct: int = 0) -> dict[str, Any]:
    if not 0 <= meat_pct <= 100:
        raise PizzaError("meat_pct must be between 0 and 100")
    return {"planned": cheapest(people, menu, each, meat_pct), "naive": cheapest_slice_only(people, menu, each)}
