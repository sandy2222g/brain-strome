"""Choose the cheapest fare option for a rider from their ride log.

Fare options, each costed over the 4-week log:
- single:     pay for every ride
- day_pass:   on each day, pay min(rides * single, day pass price)
- week_pass:  one weekly pass every week, whatever the rides
- weekly_cap: pay singles, but never more than the cap in a week (fare capping)
- month_pass: one pass for all four weeks
The cheapest option wins; ties go to the simpler option in the order listed above.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "riders.json"
OPTIONS = ("single", "day_pass", "week_pass", "weekly_cap", "month_pass")
MAX_RIDERS = 50
WEEKS = 4


class FareError(ValueError):
    """Invalid fares or ride log."""


@dataclass(frozen=True)
class Fares:
    single: float
    day_pass: float
    week_pass: float
    month_pass: float
    weekly_cap: float


@dataclass(frozen=True)
class Rider:
    name: str
    weeks: tuple[tuple[int, ...], ...]


def build(fares: dict[str, float], riders: list[dict]) -> tuple[Fares, list[Rider]]:  # type: ignore[type-arg]
    try:
        f = Fares(**{k: float(fares[k]) for k in ("single", "day_pass", "week_pass", "month_pass", "weekly_cap")})
    except (KeyError, TypeError) as err:
        raise FareError("fares need single, day_pass, week_pass, month_pass and weekly_cap") from err
    if min(f.single, f.day_pass, f.week_pass, f.month_pass, f.weekly_cap) <= 0:
        raise FareError("fares must be positive")
    if not 1 <= len(riders) <= MAX_RIDERS:
        raise FareError(f"between 1 and {MAX_RIDERS} riders")
    out = []
    for r in riders:
        weeks = tuple(tuple(int(x) for x in w) for w in r["weeks"])
        if len(weeks) != WEEKS or any(len(w) != 7 or min(w) < 0 or max(w) > 50 for w in weeks):
            raise FareError(f"{r['name']}: need {WEEKS} weeks of 7 non-negative daily ride counts")
        out.append(Rider(r["name"], weeks))
    if len({r.name for r in out}) != len(out):
        raise FareError("rider names must be unique")
    return f, out


def load(path: Path = DATA) -> tuple[Fares, list[Rider]]:
    raw = json.loads(path.read_text())
    return build(raw["fares"], raw["riders"])


def cost(fares: Fares, rider: Rider, option: str) -> float:
    rides_per_week = [sum(w) for w in rider.weeks]
    if option == "single":
        return sum(rides_per_week) * fares.single
    if option == "day_pass":
        return sum(min(d * fares.single, fares.day_pass) if d else 0 for w in rider.weeks for d in w)
    if option == "week_pass":
        return fares.week_pass * WEEKS
    if option == "weekly_cap":
        return sum(min(n * fares.single, fares.weekly_cap) for n in rides_per_week)
    if option == "month_pass":
        return fares.month_pass
    raise FareError(f"unknown option '{option}'")


def best_option(fares: Fares, rider: Rider) -> tuple[str, dict[str, float]]:
    costs = {o: round(cost(fares, rider, o), 2) for o in OPTIONS}
    best = min(OPTIONS, key=lambda o: (costs[o], OPTIONS.index(o)))
    return best, costs


def break_even_rides_per_week(fares: Fares) -> float:
    """Rides per week at which a weekly pass costs the same as paying singles."""
    return fares.week_pass / fares.single
