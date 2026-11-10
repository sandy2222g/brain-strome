"""Gear selection as a 0/1 knapsack, solved exactly by dynamic programming.

Steps: (1) conditions decide which items are *required* and how much each item is worth today;
(2) required items are packed first; (3) the remaining weight budget is filled optimally with the
rest, never choosing two items of the same exclusive group (one tent, one sleeping bag);
(4) consumables (food, water) are added on top because they depend on days and people.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

GRAM_STEP = 10
FOOD_G_PER_PERSON_DAY = 650
WATER_G = 1000  # carried per person at the start of a day (1 L)


class PackError(ValueError):
    """Bad request; message is safe to show."""


@dataclass(frozen=True)
class Trip:
    days: int = 2
    people: int = 1
    min_temp_c: float = 8.0
    rain_chance: float = 0.3
    sun: bool = True
    bugs: bool = False
    limit_kg: float = 9.0  # total carried weight limit per person, including food and water

    def validate(self) -> None:
        if not 1 <= self.days <= 14:
            raise PackError("days must be between 1 and 14")
        if not 1 <= self.people <= 8:
            raise PackError("people must be between 1 and 8")
        if not -20 <= self.min_temp_c <= 35 or not 0 <= self.rain_chance <= 1:
            raise PackError("temperature must be -20 to 35 and rain chance between 0 and 1")
        if not 3 <= self.limit_kg <= 30:
            raise PackError("limit must be between 3 and 30 kg")


@dataclass
class Item:
    id: str
    name: str
    category: str
    weight_g: int
    utility: float
    group: str
    tags: tuple[str, ...]
    required: bool = False


@dataclass
class Pack:
    chosen: list[Item]
    leave_behind: list[Item]
    gear_g: int
    food_g: int
    water_g: int
    total_g: int
    limit_g: int
    utility: float
    greedy_utility: float
    feasible: bool
    notes: list[str] = field(default_factory=list)


def load_gear(path: Path) -> list[Item]:
    df = pd.read_csv(path).fillna("")
    need = {"id", "name", "category", "weight_g", "utility", "group", "tags"}
    if need - set(df.columns):
        raise ValueError(f"missing columns: {sorted(need - set(df.columns))}")
    return [
        Item(
            str(r["id"]),
            str(r["name"]),
            str(r["category"]),
            int(r["weight_g"]),
            float(r["utility"]),
            str(r["group"]),
            tuple(x for x in str(r["tags"]).split("|") if x),
        )
        for r in df.to_dict("records")
    ]


def adjust(items: list[Item], trip: Trip) -> list[Item]:
    """Apply conditions: mark required items and scale utilities."""
    out = []
    for it in items:
        util, req = it.utility, False
        if "cold" in it.tags:
            if trip.min_temp_c <= 5:
                util, req = util + 4, it.id in {"puffy", "gloves"} or trip.min_temp_c <= -5
            elif trip.min_temp_c > 15:
                util = 0.5
        if "rain" in it.tags:
            util += 6 * trip.rain_chance
            req = req or (it.id == "jacketrain" and trip.rain_chance >= 0.25)
        if "sun" in it.tags and not trip.sun:
            util = 0.5
        if "bugs" in it.tags:
            util = util + 5 if trip.bugs else 0.2
        if it.id == "bag1" and trip.min_temp_c < 8:
            util = 1.0
        if it.id == "bag4" and trip.min_temp_c > 0:
            util = 2.0
        if it.id == "bag3" and trip.min_temp_c < -2:
            util = 3.0
        if it.id in {"stove", "pot"} and trip.days == 1:
            util *= 0.4
        if it.id in {"tent", "tarp", "bivy", "bag1", "bag3", "bag4", "pad", "padlite"} and trip.days == 1:
            util = 0.1  # day hike: no overnight kit
        out.append(Item(it.id, it.name, it.category, it.weight_g, round(util, 2), it.group, it.tags, req))
    return out


def consumables(trip: Trip) -> tuple[int, int]:
    food = FOOD_G_PER_PERSON_DAY * trip.days
    water = WATER_G * (2 if trip.sun and trip.min_temp_c > 10 else 1)
    return food, water


def _solve(items: list[Item], budget_g: int) -> tuple[float, list[Item]]:
    """Exact multiple-choice knapsack: items sharing a group are alternatives, take at most one."""
    cap = budget_g // GRAM_STEP
    groups: dict[str, list[Item]] = {}
    for it in items:
        groups.setdefault(it.group or f"_{it.id}", []).append(it)
    state: list[tuple[float, tuple[str, ...]]] = [(0.0, ())] * (cap + 1)
    for _, alts in groups.items():
        new = list(state)
        for w in range(cap + 1):
            for it in alts:
                cost = -(-it.weight_g // GRAM_STEP)
                if cost <= w:
                    u = state[w - cost][0] + it.utility
                    if u > new[w][0] + 1e-9:
                        new[w] = (u, (*state[w - cost][1], it.id))
        state = new
    score, ids = max(state, key=lambda s: s[0])
    by_id = {it.id: it for it in items}
    return score, [by_id[i] for i in ids]


def _greedy(items: list[Item], budget_g: int) -> float:
    """Baseline: best utility per gram first, one per group."""
    used_groups: set[str] = set()
    total_w, total_u = 0, 0.0
    for it in sorted(items, key=lambda i: -i.utility / i.weight_g):
        key = it.group or f"_{it.id}"
        if key in used_groups or total_w + it.weight_g > budget_g:
            continue
        used_groups.add(key)
        total_w += it.weight_g
        total_u += it.utility
    return total_u


def optimise(items: list[Item], trip: Trip) -> Pack:
    trip.validate()
    adj = adjust(items, trip)
    food, water = consumables(trip)
    limit_g = int(trip.limit_kg * 1000)
    required = [i for i in adj if i.required]
    req_w = sum(i.weight_g for i in required)
    budget = limit_g - food - water - req_w
    notes: list[str] = []
    if budget < 0:
        return Pack(
            required,
            [i for i in adj if not i.required],
            req_w,
            food,
            water,
            req_w + food + water,
            limit_g,
            sum(i.utility for i in required),
            0.0,
            False,
            ["Even the required items, food and water exceed your limit: raise the limit or shorten the trip."],
        )
    req_groups = {i.group for i in required if i.group}
    pool = [i for i in adj if not i.required and i.group not in req_groups and i.utility > 0.3]
    util, picked = _solve(pool, budget)
    chosen = required + picked
    chosen_ids = {i.id for i in chosen}
    gear = sum(i.weight_g for i in chosen)
    greedy_u = _greedy(pool, budget) + sum(i.utility for i in required)
    left = sorted([i for i in adj if i.id not in chosen_ids and i.utility > 0.3], key=lambda i: -i.utility / i.weight_g)
    if trip.min_temp_c <= 0 and not any(i.group == "bag" and i.id == "bag4" for i in chosen):
        notes.append("Freezing nights: your sleeping bag may be too light for the limit you set.")
    if gear + food + water > limit_g:
        notes.append("Over the limit.")
    return Pack(
        chosen,
        left,
        gear,
        food,
        water,
        gear + food + water,
        limit_g,
        round(util + sum(i.utility for i in required), 2),
        round(greedy_u, 2),
        True,
        notes,
    )
