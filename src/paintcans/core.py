"""Work out how much paint a job needs and the cheapest set of cans that covers it.

Litres needed = wall area x coats / coverage per litre. Cans come in a few sizes (multiples of half a litre);
an unbounded-knapsack DP finds the cheapest combination covering at least that much.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "job.json"
MAX_ROOMS = 30


class PaintError(ValueError):
    """Invalid job or can list."""


@dataclass(frozen=True)
class Room:
    name: str
    width: float
    length: float
    height: float
    openings: float = 0.0  # doors and windows, m2


def wall_area(room: Room) -> float:
    area = 2 * (room.width + room.length) * room.height - room.openings
    if area <= 0:
        raise PaintError(f"{room.name}: no wall area left")
    return area


def litres_needed(rooms: list[Room], coats: int, coverage: float) -> float:
    if not rooms or not 1 <= coats <= 4 or coverage <= 0:
        raise PaintError("need rooms, 1-4 coats and positive coverage")
    return sum(wall_area(r) for r in rooms) * coats / coverage


def cheapest_cans(litres: float, cans: dict[float, float]) -> tuple[float, dict[float, int]]:
    """Cheapest (cost, {size: count}) covering at least `litres`; sizes are multiples of 0.5 L."""
    if not cans or min(cans) <= 0 or min(cans.values()) <= 0:
        raise PaintError("cans need positive sizes and prices")
    units = {round(s * 2): p for s, p in cans.items()}
    if any(abs(u / 2 - s) > 1e-9 for u, s in zip(units, cans, strict=True)):
        raise PaintError("can sizes must be multiples of 0.5 L")
    need = math.ceil(litres * 2 - 1e-9)
    best = [(0.0, ())] + [(math.inf, ())] * need
    for u in range(1, need + 1):
        for size, price in units.items():
            prev = best[max(0, u - size)]
            if prev[0] + price < best[u][0] - 1e-9:
                best[u] = (prev[0] + price, (*prev[1], size))
    cost, chosen = best[need]
    counts: dict[float, int] = {}
    for u in chosen:
        counts[u / 2] = counts.get(u / 2, 0) + 1
    return round(cost, 2), dict(sorted(counts.items(), reverse=True))


def baseline_largest(litres: float, cans: dict[float, float]) -> tuple[float, dict[float, int]]:
    """Naive plan: only buy the biggest can size, rounding up."""
    size = max(cans)
    n = math.ceil(litres / size - 1e-9)
    return round(n * cans[size], 2), {size: n}


def baseline_smallest(litres: float, cans: dict[float, float]) -> tuple[float, dict[float, int]]:
    size = min(cans)
    n = math.ceil(litres / size - 1e-9)
    return round(n * cans[size], 2), {size: n}


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
