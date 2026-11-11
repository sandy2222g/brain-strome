"""Plan the fewest stops (then cheapest fuel) on a road trip.

Constraints: fuel stops at most `range_km` apart (start and end count as full/destination),
and some stop (any kind) at most `max_leg_km` apart so the driver gets regular breaks.
State = (last stop, last fuel stop); DP minimises (stop count, fuel price paid).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "route.json"


class TripError(ValueError):
    """No valid plan or bad input."""


@dataclass(frozen=True)
class Stop:
    name: str
    km: float
    kind: str  # fuel | break | both
    price: float = 0.0

    @property
    def fuels(self) -> bool:
        return self.kind in ("fuel", "both")


def load(path: Path = DATA) -> tuple[float, list[Stop]]:
    raw = json.loads(path.read_text())
    return raw["route"]["length_km"], [Stop(**s) for s in raw["stops"]]


def plan(length: float, stops: list[Stop], range_km: float, max_leg_km: float) -> list[Stop]:
    """Return the chosen stops in order. Raises TripError when impossible."""
    if range_km <= 0 or max_leg_km <= 0:
        raise TripError("range and leg limits must be positive")
    pts = sorted(stops, key=lambda s: s.km)
    if any(s.km <= 0 or s.km >= length for s in pts):
        raise TripError("stops must lie strictly between start and destination")

    def km(i: int) -> float:
        return 0.0 if i < 0 else pts[i].km

    # state (last stop, last fuel stop) -> (stops used, fuel price paid, previous state)
    best: dict[tuple[int, int], tuple[int, float, tuple[int, int] | None]] = {(-1, -1): (0, 0.0, None)}
    for i in range(-1, len(pts)):
        for (li, lf), (n, c, _) in [kv for kv in best.items() if kv[0][0] == i]:
            for j in range(i + 1, len(pts)):
                if pts[j].km - km(i) > max_leg_km:
                    break
                if pts[j].km - km(lf) > range_km:
                    continue
                nlf = j if pts[j].fuels else lf
                cand = (n + 1, c + (pts[j].price if pts[j].fuels else 0.0))
                key = (j, nlf)
                if key not in best or cand < best[key][:2]:
                    best[key] = (cand[0], cand[1], (li, lf))
    finals = [
        (v[0], v[1], k) for k, v in best.items() if length - km(k[0]) <= max_leg_km and length - km(k[1]) <= range_km
    ]
    if not finals:
        raise TripError("no valid plan: stops are too far apart for these limits")
    _, _, key = min(finals)
    chosen: list[Stop] = []
    cur: tuple[int, int] | None = key
    while cur is not None and cur[0] >= 0:
        chosen.append(pts[cur[0]])
        cur = best[cur][2]
    return chosen[::-1]


def validate(length: float, chosen: list[Stop], range_km: float, max_leg_km: float) -> bool:
    kms = [0.0, *[s.km for s in chosen], length]
    if any(b - a > max_leg_km for a, b in zip(kms, kms[1:], strict=False)):
        return False
    fuel = [0.0, *[s.km for s in chosen if s.fuels], length]
    return all(b - a <= range_km for a, b in zip(fuel, fuel[1:], strict=False))


def naive_plan(length: float, stops: list[Stop], range_km: float, max_leg_km: float) -> list[Stop]:
    """Baseline: stop at the furthest allowed stop each time (fuel when needed). May not be optimal."""
    pts = sorted(stops, key=lambda s: s.km)
    pos, last_fuel, out = 0.0, 0.0, []
    while length - pos > max_leg_km or length - last_fuel > range_km:
        reach = [s for s in pts if pos < s.km <= pos + max_leg_km and (not s.fuels or s.km - last_fuel <= range_km)]
        if length - last_fuel > range_km:
            fuelable = [s for s in reach if s.fuels]
            reach = fuelable or reach
        if not reach:
            raise TripError("no valid plan: stops are too far apart for these limits")
        nxt = max(reach, key=lambda s: s.km)
        out.append(nxt)
        pos = nxt.km
        if nxt.fuels:
            last_fuel = nxt.km
    return out


def summary(chosen: list[Stop]) -> dict[str, float]:
    fuel = [s for s in chosen if s.fuels]
    return {
        "stops": len(chosen),
        "fuel_stops": len(fuel),
        "avg_fuel_price": round(sum(s.price for s in fuel) / len(fuel), 3) if fuel else 0.0,
    }
