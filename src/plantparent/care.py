"""Turn plants + conditions into a watering schedule, and learn from soil checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

import pandas as pd

from plantparent.model import IntervalModel, season_for

MIN_MULT, MAX_MULT = 0.5, 2.0
SOIL_CHOICES = ("dry", "ok", "wet")


@dataclass(frozen=True)
class Plant:
    name: str
    species: str
    pot_cm: float
    material: str
    last_watered: date
    multiplier: float = 1.0  # learned from soil checks; >1 means this plant needs water less often


@dataclass
class Item:
    name: str
    species: str
    interval_days: float
    next_due: str
    days_until_due: int
    status: str  # overdue | today | soon | ok
    window_days: int
    pet_warning: bool
    tip: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify(days_until_due: int) -> str:
    if days_until_due < 0:
        return "overdue"
    if days_until_due == 0:
        return "today"
    return "soon" if days_until_due <= 2 else "ok"


def update_multiplier(multiplier: float, soil: str) -> float:
    """Soil check at watering time: 'dry' = it could have been watered sooner, 'wet' = too early."""
    if soil not in SOIL_CHOICES:
        raise ValueError(f"soil must be one of {SOIL_CHOICES}")
    factor = {"dry": 0.9, "ok": 1.0, "wet": 1.15}[soil]
    return round(min(MAX_MULT, max(MIN_MULT, multiplier * factor)), 3)


def schedule(
    plants: list[Plant],
    species_df: pd.DataFrame,
    model: IntervalModel,
    today: date,
    hemisphere: str = "north",
    temp_c: float = 21.0,
    humidity: float = 45.0,
    light_by_species: bool = True,
    pets: bool = False,
    horizon_days: int = 30,
) -> dict[str, Any]:
    info = species_df.set_index("species")
    rows = []
    for p in plants:
        if p.species not in info.index:
            raise KeyError(p.species)
        s = info.loc[p.species]
        rows.append(
            {
                "base_days": float(s["base_days"]),
                "pot_cm": p.pot_cm,
                "temp_c": temp_c,
                "humidity": humidity,
                "material": p.material,
                "light": str(s["light"]) if light_by_species else "medium",
                "season": season_for(today.month, hemisphere),
            }
        )
    base_intervals = model.predict_days(rows) if rows else []
    items: list[Item] = []
    calendar: dict[str, list[str]] = {}
    for p, base in zip(plants, base_intervals, strict=True):
        interval = max(1.0, float(base) * p.multiplier)
        step = max(1, round(interval))
        due = p.last_watered + timedelta(days=step)
        until = (due - today).days
        s = info.loc[p.species]
        items.append(
            Item(
                name=p.name,
                species=p.species,
                interval_days=round(interval, 1),
                next_due=due.isoformat(),
                days_until_due=until,
                status=classify(until),
                window_days=max(1, round(interval * model.rel_error_p80)),
                pet_warning=bool(pets and not int(s["pet_safe"])),
                tip=str(s["tip"]),
            )
        )
        d = due
        while (d - today).days <= horizon_days:
            if d >= today:
                calendar.setdefault(d.isoformat(), []).append(p.name)
            d += timedelta(days=step)
    items.sort(key=lambda i: (i.days_until_due, i.name))
    return {
        "season": season_for(today.month, hemisphere),
        "items": [i.to_dict() for i in items],
        "water_today": [i.name for i in items if i.status in ("overdue", "today")],
        "calendar": dict(sorted(calendar.items())),
        "pet_warnings": [i.name for i in items if i.pet_warning],
    }
