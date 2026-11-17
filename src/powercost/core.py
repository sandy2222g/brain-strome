"""Monthly cost per appliance, and the saving from moving shiftable loads off-peak."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "home.json"


class PowerError(ValueError):
    """Raised for invalid appliances or tariffs."""


def load() -> dict[str, Any]:
    return json.loads(DATA.read_text())


def kwh_per_month(a: dict[str, Any], days: int) -> float:
    watts, hours, share = float(a["watts"]), float(a["hours_per_day"]), float(a["peak_share"])
    if watts <= 0 or not 0 <= hours <= 24 or not 0 <= share <= 1:
        raise PowerError(f"bad numbers for {a['name']!r}")
    return watts * hours / 1000 * days


def cost(a: dict[str, Any], days: int, tariff: dict[str, float], shifted: bool = False) -> float:
    """Cost with time-of-use rates; `shifted` moves all of a shiftable appliance's use off-peak."""
    if min(tariff["peak"], tariff["off_peak"], tariff["flat"]) < 0:
        raise PowerError("rates cannot be negative")
    kwh = kwh_per_month(a, days)
    share = 0.0 if shifted and a.get("shiftable") else float(a["peak_share"])
    return round(kwh * (share * tariff["peak"] + (1 - share) * tariff["off_peak"]), 2)


def report(home: dict[str, Any]) -> dict[str, Any]:
    days, tariff, items = int(home["days"]), home["tariff"], home["appliances"]
    if not items or days < 1:
        raise PowerError("need appliances and a positive number of days")
    rows = []
    for a in items:
        now, moved = cost(a, days, tariff), cost(a, days, tariff, shifted=True)
        flat = round(kwh_per_month(a, days) * tariff["flat"], 2)
        rows.append(
            {"name": a["name"], "kwh": round(kwh_per_month(a, days), 1), "cost": now, "flat_cost": flat,
             "shifted_cost": moved, "saving": round(now - moved, 2)}
        )
    rows.sort(key=lambda r: (-r["cost"], r["name"]))
    return {
        "rows": rows,
        "total": round(sum(r["cost"] for r in rows), 2),
        "total_flat": round(sum(r["flat_cost"] for r in rows), 2),
        "total_saving": round(sum(r["saving"] for r in rows), 2),
    }
