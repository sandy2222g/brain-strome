"""Frost-date planting calendar: sowing windows, succession sowing, harvest conflicts, bed layout."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "crops.json"


class PlanError(ValueError):
    """Invalid planting request."""


@dataclass(frozen=True)
class Crop:
    name: str
    sow_weeks_from_frost: int
    days_to_harvest: int
    frost_tender: bool
    succession_weeks: int
    max_heat_c: float
    companions: tuple[str, ...] = ()
    avoid: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Sowing:
    crop: str
    sow: date
    harvest: date


def load_crops(path: Path = DATA) -> dict[str, Crop]:
    raw = json.loads(path.read_text())["crops"]
    return {c["name"]: Crop(**{**c, "companions": tuple(c["companions"]), "avoid": tuple(c["avoid"])}) for c in raw}


def sowing_plan(crop: Crop, last_frost: date, first_frost: date, hot_from: date | None = None) -> list[Sowing]:
    """All sowing dates: first at the crop's offset from last frost, then every succession_weeks.

    A sowing is kept only if it can be harvested before the first autumn frost (frost-tender crops)
    and, for cool-season crops, before hot weather starts (hot_from).
    """
    if first_frost <= last_frost:
        raise PlanError("first frost must be after last frost")
    start = last_frost + timedelta(weeks=crop.sow_weeks_from_frost)
    step = timedelta(weeks=crop.succession_weeks) if crop.succession_weeks else None
    out: list[Sowing] = []
    d = start
    while True:
        harvest = d + timedelta(days=crop.days_to_harvest)
        if harvest > first_frost:
            break
        if hot_from and crop.max_heat_c < 26 and harvest > hot_from:
            break
        out.append(Sowing(crop.name, d, harvest))
        if step is None:
            break
        d += step
    return out


def conflicts(names: list[str], crops: dict[str, Crop]) -> list[tuple[str, str]]:
    """Pairs that should not share a bed (either crop lists the other under `avoid`)."""
    bad = set()
    for a in names:
        for b in crops[a].avoid:
            if b in names:
                bad.add(tuple(sorted((a, b))))
    return sorted(bad)


def layout(names: list[str], crops: dict[str, Crop], beds: int) -> list[list[str]]:
    """Assign crops to beds: never put avoid-pairs together; keep companions together; balance bed sizes."""
    if beds < 1:
        raise PlanError("need at least one bed")
    out: list[list[str]] = [[] for _ in range(beds)]
    for name in sorted(names, key=lambda n: (-len(crops[n].avoid), n)):

        def score(i: int, name: str = name) -> tuple[int, int, int]:
            bed = out[i]
            clash = sum(1 for o in bed if o in crops[name].avoid or name in crops[o].avoid)
            friends = sum(1 for o in bed if o in crops[name].companions or name in crops[o].companions)
            return (clash, -friends, len(bed))

        out[min(range(beds), key=score)].append(name)
    return out


def build(
    names: list[str], last_frost: date, first_frost: date, beds: int, hot_from: date | None = None
) -> dict[str, object]:
    crops = load_crops()
    unknown = [n for n in names if n not in crops]
    if unknown:
        raise PlanError(f"unknown crops: {', '.join(unknown)}")
    if not names:
        raise PlanError("pick at least one crop")
    plan = {n: sowing_plan(crops[n], last_frost, first_frost, hot_from) for n in names}
    return {"plan": plan, "layout": layout(names, crops, beds), "conflicts": conflicts(names, crops)}
