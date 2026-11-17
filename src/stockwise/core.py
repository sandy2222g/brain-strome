"""Reorder-point inventory policy for perishables, tested by simulation against a weekly fixed order."""

from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
TRAIN_DAYS = 90


class StockError(ValueError):
    """Invalid input."""


@dataclass(frozen=True)
class Item:
    name: str
    shelf_life: int
    lead: int
    cost: float


def load_items(path: Path = DATA / "ingredients.csv") -> dict[str, Item]:
    with path.open() as fh:
        return {r["name"]: Item(r["name"], int(r["shelf_life_days"]), int(r["lead_days"]), float(r["unit_cost"]))
                for r in csv.DictReader(fh)}


def load_demand(path: Path = DATA / "demand.csv") -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    with path.open() as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["ingredient"], []).append(int(r["units"]))
    return out


def z_score(service: float) -> float:
    """Inverse of the standard normal CDF by bisection (no scipy needed)."""
    if not 0.5 <= service < 1:
        raise StockError("service level must be within [0.5, 1)")
    lo, hi = 0.0, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < service:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def plan(item: Item, history: list[int], service: float = 0.95) -> dict[str, float]:
    if len(history) < 14:
        raise StockError("need at least 14 days of demand history")
    mean, sd = statistics.fmean(history), statistics.pstdev(history)
    z = z_score(service)
    cover = item.lead + 1  # orders are placed at end of day, so they land lead + 1 days later
    safety = z * sd * math.sqrt(cover)
    rop = mean * cover + safety
    cap = mean * item.shelf_life * 0.8  # never hold more than ~80% of a shelf life of stock
    up_to = min(rop + mean * 2, cap)
    return {"mean": round(mean, 2), "sd": round(sd, 2), "safety": round(safety, 1), "reorder_point": round(rop, 1),
            "order_up_to": round(max(up_to, rop), 1), "z": round(z, 3)}


def simulate(item: Item, train: list[int], test: list[int], policy: str, service: float = 0.95) -> dict[str, float]:
    """Run the policy over the test days; FIFO stock expires after shelf_life days."""
    if policy not in ("smart", "weekly"):
        raise StockError("policy must be smart or weekly")
    p = plan(item, train, service)
    batches: list[list[int]] = [[round(sum(train[-7:])), 0]]  # [units, age] opening stock
    pipeline: list[tuple[int, int]] = []  # (arrival day, units)
    short_days = short_units = waste = 0
    stock_days = 0.0
    seen = list(train)
    for day, demand in enumerate(test):
        for _, q in [x for x in pipeline if x[0] == day]:
            batches.append([q, 0])
        pipeline = [x for x in pipeline if x[0] != day]
        need = demand
        for b in batches:
            take = min(b[0], need)
            b[0] -= take
            need -= take
        if need:
            short_days += 1
            short_units += need
        batches = [b for b in batches if b[0] > 0]
        for b in batches:
            b[1] += 1
        waste += sum(b[0] for b in batches if b[1] >= item.shelf_life)
        batches = [b for b in batches if b[1] < item.shelf_life]
        on_hand = sum(b[0] for b in batches)
        stock_days += on_hand
        seen.append(demand)
        position = on_hand + sum(q for _, q in pipeline)
        if policy == "smart" and position <= p["reorder_point"]:
            pipeline.append((day + item.lead + 1, max(0, round(p["order_up_to"] - position))))
        elif policy == "weekly" and day % 7 == 0:
            pipeline.append((day + item.lead + 1, sum(seen[-7:])))
    n = len(test)
    return {"short_days": short_days, "short_units": short_units, "waste_units": waste,
            "waste_cost": round(waste * item.cost, 2), "avg_stock": round(stock_days / n, 1),
            "service_days": round(1 - short_days / n, 3)}


def evaluate(service: float = 0.95) -> dict[str, object]:
    items, demand = load_items(), load_demand()
    rows = []
    tot = {"smart": [0, 0.0], "weekly": [0, 0.0]}
    for name, item in items.items():
        tr, te = demand[name][:TRAIN_DAYS], demand[name][TRAIN_DAYS:]
        s, w = simulate(item, tr, te, "smart", service), simulate(item, tr, te, "weekly", service)
        rows.append({"name": name, "plan": plan(item, tr, service), "smart": s, "weekly": w})
        for k, r in (("smart", s), ("weekly", w)):
            tot[k][0] += int(r["short_days"])
            tot[k][1] += float(r["waste_cost"])
    return {"service": service, "items": rows, "totals": {k: {"short_days": v[0], "waste_cost": round(v[1], 2)}
                                                          for k, v in tot.items()}}
