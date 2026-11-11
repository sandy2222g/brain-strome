"""Split the fare of a shared taxi fairly using Shapley values.

The taxi starts at a station and drops each rider at their stop, visiting stops in the cheapest order. The cost of
a group is the length of that cheapest open route times the rate. The Shapley value charges each rider their
average extra cost when they join the ride, over every order in which riders could have joined. It always adds up
to the real fare, and nobody pays more than riding alone.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import cache
from itertools import permutations
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "ride.json"
MAX_RIDERS = 7


class FareError(ValueError):
    """Invalid ride."""


@dataclass(frozen=True)
class Rider:
    name: str
    stop: tuple[float, float]


@dataclass(frozen=True)
class Ride:
    riders: tuple[Rider, ...]
    start: tuple[float, float]
    rate_per_km: float


def build(riders: list[Rider], start: tuple[float, float], rate_per_km: float) -> Ride:
    if not 1 <= len(riders) <= MAX_RIDERS:
        raise FareError(f"between 1 and {MAX_RIDERS} riders")
    if len({r.name for r in riders}) != len(riders):
        raise FareError("rider names must be unique")
    if rate_per_km <= 0:
        raise FareError("rate must be positive")
    return Ride(tuple(riders), start, rate_per_km)


def load(path: Path = DATA) -> Ride:
    raw = json.loads(path.read_text())
    return build(
        [Rider(r["name"], (r["stop"][0], r["stop"][1])) for r in raw["riders"]], tuple(raw["start"]), raw["rate_per_km"]
    )


def _route_km(start: tuple[float, float], stops: tuple[tuple[float, float], ...]) -> float:
    """Shortest open route from `start` visiting every stop (exact, by trying all orders)."""
    if not stops:
        return 0.0
    best = math.inf
    for order in permutations(stops):
        pos, total = start, 0.0
        for s in order:
            total += math.dist(pos, s)
            pos = s
        best = min(best, total)
    return best


def group_cost(ride: Ride, members: frozenset[int]) -> float:
    return _group_cost(ride, tuple(sorted(members)))


@cache
def _group_cost(ride: Ride, members: tuple[int, ...]) -> float:
    return _route_km(ride.start, tuple(ride.riders[i].stop for i in members)) * ride.rate_per_km


def total_fare(ride: Ride) -> float:
    return group_cost(ride, frozenset(range(len(ride.riders))))


def alone_cost(ride: Ride, i: int) -> float:
    return group_cost(ride, frozenset({i}))


def equal_split(ride: Ride) -> list[float]:
    n = len(ride.riders)
    return [total_fare(ride) / n] * n


def distance_split(ride: Ride) -> list[float]:
    """Share the fare in proportion to each rider's own straight-line distance from the station."""
    d = [math.dist(ride.start, r.stop) for r in ride.riders]
    total = sum(d)
    return [total_fare(ride) * x / total for x in d]


def shapley(ride: Ride) -> list[float]:
    """Average marginal cost over all n! orders in which the riders could have been picked up."""
    n = len(ride.riders)
    owed = [0.0] * n
    count = 0
    for order in permutations(range(n)):
        so_far: frozenset[int] = frozenset()
        for i in order:
            owed[i] += group_cost(ride, so_far | {i}) - group_cost(ride, so_far)
            so_far = so_far | {i}
        count += 1
    return [x / count for x in owed]
