"""Place books, kept in reading order, on shelves of fixed width using the least total shelf height."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "books.json"


class ShelfError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def _books(raw: list[dict[str, Any]], width: float) -> list[tuple[str, float, float]]:
    if width <= 0:
        raise ShelfError("shelf width must be positive")
    if not raw:
        raise ShelfError("no books")
    out = []
    for b in raw:
        t, h = float(b["thickness"]), float(b["height"])
        if t <= 0 or h <= 0:
            raise ShelfError("thickness and height must be positive")
        if t > width:
            raise ShelfError(f"{b['title']} is thicker than the shelf")
        out.append((str(b["title"]), t, h))
    return out


def _result(books: list[tuple[str, float, float]], cuts: list[int]) -> dict[str, Any]:
    shelves = []
    for a, b in zip(cuts, cuts[1:], strict=False):
        part = books[a:b]
        shelves.append({
            "books": [t for t, _, _ in part],
            "used": sum(w for _, w, _ in part),
            "height": max(h for _, _, h in part),
        })
    return {"shelves": shelves, "total_height": sum(s["height"] for s in shelves), "count": len(shelves)}


def optimal(raw: list[dict[str, Any]], width: float) -> dict[str, Any]:
    """Dynamic programme: best[i] = least total height for the first i books; the last shelf is books j..i-1."""
    books = _books(raw, width)
    n = len(books)
    best = [0.0] + [float("inf")] * n
    cut = [0] * (n + 1)
    for i in range(1, n + 1):
        used, tall = 0.0, 0.0
        for j in range(i - 1, -1, -1):
            used += books[j][1]
            if used > width:
                break
            tall = max(tall, books[j][2])
            if best[j] + tall < best[i]:
                best[i], cut[i] = best[j] + tall, j
    cuts = [n]
    while cuts[-1] > 0:
        cuts.append(cut[cuts[-1]])
    return _result(books, cuts[::-1])


def greedy(raw: list[dict[str, Any]], width: float) -> dict[str, Any]:
    """Baseline: fill each shelf until the next book no longer fits."""
    books = _books(raw, width)
    cuts, used = [0], 0.0
    for i, (_, t, _) in enumerate(books):
        if used + t > width:
            cuts.append(i)
            used = 0.0
        used += t
    cuts.append(len(books))
    return _result(books, cuts)


def compare(raw: list[dict[str, Any]], width: float) -> dict[str, Any]:
    o, g = optimal(raw, width), greedy(raw, width)
    return {"optimal": o, "greedy": g, "height_saved": g["total_height"] - o["total_height"]}
