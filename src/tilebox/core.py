"""How many boxes of floor tiles to buy for a room, allowing for cuts and breakages.

Tiles needed = floor area / tile area; waste allowance depends on the layout (straight 10%, diagonal 15%).
The answer is the number of whole boxes; spare tiles are reported so you can keep them for repairs.
Buying with no allowance is the naive plan and usually leaves the last row unfinished.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "room.json"
WASTE = {"straight": 0.10, "diagonal": 0.15}


class TileError(ValueError):
    """Invalid room or tile."""


@dataclass(frozen=True)
class Job:
    width_m: float
    length_m: float
    tile_cm: float
    tiles_per_box: int
    box_price: float
    layout: str


def build(raw: dict) -> Job:  # type: ignore[type-arg]
    try:
        j = Job(
            float(raw["width_m"]),
            float(raw["length_m"]),
            float(raw["tile_cm"]),
            int(raw["tiles_per_box"]),
            float(raw["box_price"]),
            str(raw.get("layout", "straight")),
        )
    except (KeyError, ValueError, TypeError) as err:
        raise TileError("need width_m, length_m, tile_cm, tiles_per_box, box_price") from err
    if min(j.width_m, j.length_m, j.tile_cm, j.tiles_per_box, j.box_price) <= 0 or j.layout not in WASTE:
        raise TileError("positive sizes and prices; layout straight or diagonal")
    if j.width_m > 50 or j.length_m > 50 or j.tile_cm > 200:
        raise TileError("room up to 50 m a side, tiles up to 200 cm")
    return j


def tiles_for_floor(j: Job) -> int:
    """Whole tiles that cover the floor with no allowance (rows and columns rounded up)."""
    side = j.tile_cm / 100
    return math.ceil(j.width_m / side - 1e-9) * math.ceil(j.length_m / side - 1e-9)


def boxes_needed(tiles: int, per_box: int) -> int:
    return math.ceil(tiles / per_box)


def plan(j: Job) -> dict[str, float | int]:
    floor = tiles_for_floor(j)
    with_waste = math.ceil(floor * (1 + WASTE[j.layout]) - 1e-9)
    boxes = boxes_needed(with_waste, j.tiles_per_box)
    naive_boxes = boxes_needed(floor, j.tiles_per_box)
    return {
        "floor_tiles": floor,
        "tiles_with_waste": with_waste,
        "boxes": boxes,
        "cost": round(boxes * j.box_price, 2),
        "spare_tiles": boxes * j.tiles_per_box - floor,
        "naive_boxes": naive_boxes,
        "naive_spare_after_cuts": naive_boxes * j.tiles_per_box - with_waste,
    }


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
