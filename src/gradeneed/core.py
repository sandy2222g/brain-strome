"""Work out the score needed on the remaining work to reach each grade band (invented course)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "course.json"


class GradeError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def category_average(scores: list[float], drop_lowest: int) -> float | None:
    """Mean after dropping the lowest scores, never dropping a category down to nothing."""
    if not scores:
        return None
    drop = min(drop_lowest, len(scores) - 1)
    kept = sorted(scores)[drop:]
    return sum(kept) / len(kept)


def _validate(cats: list[dict[str, Any]], bands: dict[str, float]) -> None:
    if not cats:
        raise GradeError("no categories")
    if abs(sum(c["weight"] for c in cats) - 100) > 1e-9:
        raise GradeError("weights must add up to 100")
    for c in cats:
        if c["weight"] <= 0 or c["drop_lowest"] < 0:
            raise GradeError(f"bad weight or drop count in {c['name']}")
        if any(not 0 <= s <= 100 for s in c["scores"]):
            raise GradeError(f"scores in {c['name']} must be 0-100")
    if not bands:
        raise GradeError("no grade bands")


def analyse(cats: list[dict[str, Any]], bands: dict[str, float]) -> dict[str, Any]:
    """Current standing on finished work, and the average needed on unfinished categories per band."""
    _validate(cats, bands)
    rows, earned, done_w, open_w = [], 0.0, 0.0, 0.0
    for c in cats:
        avg = category_average(c["scores"], c["drop_lowest"])
        rows.append({"name": c["name"], "weight": c["weight"], "average": None if avg is None else round(avg, 2)})
        if avg is None:
            open_w += c["weight"]
        else:
            earned += avg * c["weight"] / 100
            done_w += c["weight"]
    needed = {}
    for band, cut in sorted(bands.items(), key=lambda kv: -kv[1]):
        if open_w == 0:
            needed[band] = {"needed": None, "status": "secured" if earned >= cut else "missed"}
            continue
        need = (cut - earned) * 100 / open_w
        status = "secured" if need <= 0 else "impossible" if need > 100 else "possible"
        needed[band] = {"needed": round(max(need, 0), 2), "status": status}
    return {
        "categories": rows,
        "points_earned": round(earned, 2),
        "weight_done": done_w,
        "standing": round(earned * 100 / done_w, 2) if done_w else None,
        "needed": needed,
    }


def naive_mean(cats: list[dict[str, Any]]) -> float | None:
    """Baseline: plain average of every score so far, ignoring weights and drop rules."""
    every = [s for c in cats for s in c["scores"]]
    return round(sum(every) / len(every), 2) if every else None
