"""Single-lift discrete-event simulation with three dispatch policies."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "arrivals.csv"
POLICIES = ("fcfs", "nearest", "scan")
TRAVEL_S = 2  # seconds per floor
STOP_S = 5  # seconds for doors when anyone gets on or off


class LiftError(ValueError):
    """Invalid input."""


@dataclass
class Person:
    t: int
    origin: int
    dest: int
    boarded: int = -1
    arrived: int = -1


def load(path: Path = DATA) -> list[Person]:
    with path.open() as fh:
        return [Person(int(r["time_s"]), int(r["origin"]), int(r["dest"])) for r in csv.DictReader(fh)]


def pct(vals: list[int], q: float) -> int:
    s = sorted(vals)
    return s[max(0, math.ceil(q * len(s)) - 1)]


def simulate(people: list[Person], policy: str, floors: int = 12, capacity: int = 8) -> dict[str, float]:
    if policy not in POLICIES:
        raise LiftError(f"policy must be one of {POLICIES}")
    if not people or floors < 2 or capacity < 1:
        raise LiftError("need people, floors >= 2 and capacity >= 1")
    if any(not (0 <= p.origin < floors and 0 <= p.dest < floors and p.origin != p.dest) for p in people):
        raise LiftError("origin and dest must be different floors within the building")
    ps = sorted((Person(p.t, p.origin, p.dest) for p in people), key=lambda p: p.t)
    pending, waiting, onboard = list(ps), [], []
    time, floor, direction = 0, 0, 1
    while pending or waiting or onboard:
        while pending and pending[0].t <= time:
            waiting.append(pending.pop(0))
        moved = False
        for p in [p for p in onboard if p.dest == floor]:
            p.arrived = time
            onboard.remove(p)
            moved = True
        for p in [p for p in waiting if p.origin == floor][: capacity - len(onboard)]:
            p.boarded = time
            waiting.remove(p)
            onboard.append(p)
            moved = True
        if moved:
            time += STOP_S
            continue
        cands = {p.dest for p in onboard}
        if len(onboard) < capacity:  # a full lift cannot pick anyone up, so it only heads for drop-offs
            cands |= {p.origin for p in waiting if p.origin != floor}
        if not cands:
            time = pending[0].t if pending else time
            continue
        if policy == "fcfs":
            first = onboard[0].dest if onboard else min(waiting, key=lambda p: p.t).origin
            target = first
        elif policy == "nearest":
            target = min(cands, key=lambda f: (abs(f - floor), f))
        else:
            ahead = [f for f in cands if (f - floor) * direction > 0]
            if not ahead:
                direction = -direction
                ahead = [f for f in cands if (f - floor) * direction > 0]
            target = min(ahead, key=lambda f: abs(f - floor))
        floor += 1 if target > floor else -1
        time += TRAVEL_S
    waits = [p.boarded - p.t for p in ps]
    rides = [p.arrived - p.boarded for p in ps]
    return {"mean_wait": round(sum(waits) / len(waits), 1), "p90_wait": pct(waits, 0.9),
            "max_wait": max(waits), "mean_ride": round(sum(rides) / len(rides), 1), "finish_s": time}


def compare(people: list[Person] | None = None, floors: int = 12, capacity: int = 8) -> dict[str, dict[str, float]]:
    ps = people if people is not None else load()
    return {p: simulate(ps, p, floors, capacity) for p in POLICIES}
