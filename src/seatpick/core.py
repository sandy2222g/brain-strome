"""Score free blocks of seats by distance from the ideal spot and pick the best."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "hall.json"


class SeatError(ValueError):
    """Raised for invalid halls or party sizes."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def _check(rows: list[str]) -> None:
    if not rows or len({len(r) for r in rows}) != 1 or not rows[0]:
        raise SeatError("rows must be non-empty and of equal length")
    if any(set(r) - {"X", "."} for r in rows):
        raise SeatError("rows may only contain 'X' and '.'")


def score(rows: list[str], row: int, start: int, size: int) -> float:
    """Lower is better: distance of the block centre from the ideal spot (2/3 of the way back, middle)."""
    n_rows, n_cols = len(rows), len(rows[0])
    ideal_row = (n_rows - 1) * 2 / 3
    centre = start + (size - 1) / 2
    return round(abs(row - ideal_row) * 1.5 + abs(centre - (n_cols - 1) / 2), 3)


def blocks(rows: list[str], size: int) -> list[dict[str, Any]]:
    """Every run of `size` free seats side by side, best first (ties: lower row, then lower seat)."""
    _check(rows)
    if size < 1 or size > len(rows[0]):
        raise SeatError("party size does not fit a row")
    out = []
    for r, line in enumerate(rows):
        for c in range(len(line) - size + 1):
            if "X" not in line[c : c + size]:
                out.append({"row": r, "start": c, "size": size, "score": score(rows, r, c, size)})
    out.sort(key=lambda b: (b["score"], b["row"], b["start"]))
    return out


def best(rows: list[str], size: int) -> dict[str, Any] | None:
    found = blocks(rows, size)
    return found[0] if found else None


def first_free(rows: list[str], size: int) -> dict[str, Any] | None:
    """Baseline: the first block found reading from the front-left."""
    found = sorted(blocks(rows, size), key=lambda b: (b["row"], b["start"]))
    return found[0] if found else None


def mark(rows: list[str], block: dict[str, Any] | None) -> list[str]:
    """Draw the chosen block as 'O' on the seat map."""
    if block is None:
        return list(rows)
    out = list(rows)
    line = out[block["row"]]
    out[block["row"]] = line[: block["start"]] + "O" * block["size"] + line[block["start"] + block["size"] :]
    return out
