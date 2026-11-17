"""Maximum bipartite matching (augmenting paths) of guests to dish slots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "party.json"


class PotluckError(ValueError):
    """Raised for invalid guests or needs."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _slots(needs: dict[str, int]) -> list[str]:
    if not needs or any(int(n) < 1 for n in needs.values()):
        raise PotluckError("every dish category needs at least one slot")
    return [f"{cat}#{i + 1}" for cat in sorted(needs) for i in range(int(needs[cat]))]


def _check(guests: list[dict[str, Any]], needs: dict[str, int]) -> None:
    if not guests:
        raise PotluckError("need at least one guest")
    names = [g["name"] for g in guests]
    if len(set(names)) != len(names):
        raise PotluckError("guest names must be unique")
    for g in guests:
        unknown = [c for c in g["can"] if c not in needs]
        if unknown:
            raise PotluckError(f"{g['name']!r} offers unknown dish type(s) {unknown}")


def match(guests: list[dict[str, Any]], needs: dict[str, int]) -> dict[str, Any]:
    """Fill as many dish slots as possible, one dish per guest (Kuhn's augmenting-path algorithm)."""
    _check(guests, needs)
    slots = _slots(needs)
    owner: dict[str, str] = {}  # slot -> guest

    def try_guest(name: str, seen: set[str]) -> bool:
        guest = next(g for g in guests if g["name"] == name)
        for slot in slots:
            if slot.split("#")[0] in guest["can"] and slot not in seen:
                seen.add(slot)
                if slot not in owner or try_guest(owner[slot], seen):
                    owner[slot] = name
                    return True
        return False

    for g in sorted(guests, key=lambda g: (len(g["can"]), g["name"])):  # pickiest guests first
        try_guest(g["name"], set())
    return _report(slots, owner, guests)


def first_come(guests: list[dict[str, Any]], needs: dict[str, int]) -> dict[str, Any]:
    """Baseline: each guest, in order, takes the first open slot they can bring and never swaps later."""
    _check(guests, needs)
    slots = _slots(needs)
    owner: dict[str, str] = {}
    for g in guests:
        for cat in g["can"]:
            free = next((s for s in slots if s.startswith(cat + "#") and s not in owner), None)
            if free:
                owner[free] = g["name"]
                break
    return _report(slots, owner, guests)


def _report(slots: list[str], owner: dict[str, str], guests: list[dict[str, Any]]) -> dict[str, Any]:
    by_cat: dict[str, list[str]] = {}
    for s in slots:
        by_cat.setdefault(s.split("#")[0], []).append(owner.get(s, ""))
    assigned = set(owner.values())
    return {
        "assignment": by_cat,
        "filled": len(owner),
        "slots": len(slots),
        "missing": sorted(s for s in slots if s not in owner),
        "unassigned_guests": sorted(g["name"] for g in guests if g["name"] not in assigned),
    }
