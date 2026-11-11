"""Cheapest on/off heating schedule that meets comfort targets.

Model: indoor temperature T changes each hour by  -loss*(T - outdoor) + gain*heater_on.
We optimise by dynamic programming over (hour, temperature rounded to 0.1 C) with heater on/off,
minimising energy cost plus a large penalty for each degree below the comfort target while home.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "day.json"
STEP = 0.1
PENALTY = 4.0  # cost per degree-hour below target while someone is home
HOT_PENALTY = 1.0  # cost per degree-hour more than HOT_MARGIN above target while home
HOT_MARGIN = 1.5


class HeatError(ValueError):
    """Invalid configuration."""


@dataclass(frozen=True)
class House:
    loss_per_h: float
    heater_gain_c_per_h: float
    heater_kw: float
    start_temp: float


@dataclass(frozen=True)
class Day:
    house: House
    outdoor: list[float]
    price: list[float]
    comfort: list[tuple[float, float, float]]  # (from hour-of-day, to hour-of-day, target C)

    @property
    def hours(self) -> int:
        return len(self.outdoor)


def load(path: Path = DATA) -> Day:
    raw = json.loads(path.read_text())
    return validate(Day(House(**raw["house"]), raw["outdoor"], raw["price"], [tuple(c) for c in raw["comfort"]]))


def validate(day: Day) -> Day:
    if len(day.outdoor) != len(day.price) or not day.outdoor:
        raise HeatError("outdoor and price must have the same non-zero length")
    h = day.house
    if h.loss_per_h <= 0 or h.heater_gain_c_per_h <= 0 or h.heater_kw <= 0:
        raise HeatError("house parameters must be positive")
    return day


def target_at(day: Day, hour: int) -> float | None:
    hod = hour % 24
    for lo, hi, t in day.comfort:
        if lo <= hod < hi:
            return t
    return None


def step_temp(house: House, temp: float, outdoor: float, on: bool) -> float:
    return temp - house.loss_per_h * (temp - outdoor) + (house.heater_gain_c_per_h if on else 0.0)


def snap(t: float) -> float:
    return round(round(t / STEP) * STEP, 1)


def hour_cost(day: Day, hour: int, temp_after: float, on: bool) -> tuple[float, float]:
    """(energy cost, discomfort penalty) for one hour."""
    energy = day.house.heater_kw * day.price[hour] if on else 0.0
    tgt = target_at(day, hour)
    if tgt is None:
        return energy, 0.0
    short = max(0.0, tgt - temp_after)
    hot = max(0.0, temp_after - tgt - HOT_MARGIN)
    return energy, PENALTY * short + HOT_PENALTY * hot


def simulate(day: Day, schedule: list[bool]) -> dict[str, object]:
    t = day.house.start_temp
    temps, energy, disc, cold, hot = [], 0.0, 0.0, 0.0, 0.0
    for h, on in enumerate(schedule):
        t = step_temp(day.house, t, day.outdoor[h], on)
        e, p = hour_cost(day, h, t, on)
        energy, disc = energy + e, disc + p
        tgt = target_at(day, h)
        if tgt is not None:
            cold += max(0.0, tgt - t)
            hot += max(0.0, t - tgt - HOT_MARGIN)
        temps.append(round(t, 2))
    return {
        "temps": temps,
        "energy_cost": round(energy, 3),
        "cold_degree_hours": round(cold, 2),
        "overheat_degree_hours": round(hot, 2),
        "kwh": round(sum(schedule) * day.house.heater_kw, 1),
        "total": round(energy + disc, 3),
    }


def optimise(day: Day) -> list[bool]:
    """Exact DP over snapped temperatures (state space is small and bounded)."""
    start = snap(day.house.start_temp)
    layer: dict[float, tuple[float, list[bool]]] = {start: (0.0, [])}
    for h in range(day.hours):
        nxt: dict[float, tuple[float, list[bool]]] = {}
        for t, (cost, path) in layer.items():
            for on in (False, True):
                t2 = step_temp(day.house, t, day.outdoor[h], on)
                e, p = hour_cost(day, h, t2, on)
                key = snap(t2)
                c = cost + e + p
                if key not in nxt or c < nxt[key][0]:
                    nxt[key] = (c, [*path, on])
        layer = nxt
    return min(layer.values(), key=lambda v: v[0])[1]


def thermostat(day: Day, setpoint: float, band: float = 0.5) -> list[bool]:
    """Baseline: a 24/7 on/off thermostat holding `setpoint` with hysteresis."""
    t, on, out = day.house.start_temp, False, []
    for h in range(day.hours):
        if t < setpoint - band:
            on = True
        elif t > setpoint + band:
            on = False
        out.append(on)
        t = step_temp(day.house, t, day.outdoor[h], on)
    return out
