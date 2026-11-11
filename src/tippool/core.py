"""Split a tip pool by hours worked, to the cent, with the largest-remainder method.

Naive rounding of each share can make the payouts add up to a cent more or less than the pool.
Largest remainder gives everyone the rounded-down share, then hands the leftover cents to the
biggest fractional remainders (ties: earlier in the list), so the total is always exact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "tips.json"


class TipError(ValueError):
    """Invalid pool or hours."""


@dataclass(frozen=True)
class Worker:
    name: str
    hours: float


def build(workers: list[dict], pool_cents: int) -> list[Worker]:  # type: ignore[type-arg]
    if not 1 <= len(workers) <= 50 or not 0 <= pool_cents <= 10_000_000:
        raise TipError("1-50 workers and a pool of 0-100,000.00")
    out = [Worker(str(w["name"]), float(w["hours"])) for w in workers]
    if any(w.hours <= 0 for w in out) or len({w.name for w in out}) != len(out):
        raise TipError("hours must be positive and names unique")
    return out


def largest_remainder(workers: list[Worker], pool_cents: int) -> dict[str, int]:
    total = sum(w.hours for w in workers)
    exact = [pool_cents * w.hours / total for w in workers]
    base = [int(x) for x in exact]
    left = pool_cents - sum(base)
    order = sorted(range(len(workers)), key=lambda i: (-(exact[i] - base[i]), i))
    for i in order[:left]:
        base[i] += 1
    return {w.name: base[i] for i, w in enumerate(workers)}


def naive_rounding(workers: list[Worker], pool_cents: int) -> dict[str, int]:
    total = sum(w.hours for w in workers)
    return {w.name: round(pool_cents * w.hours / total) for w in workers}


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
