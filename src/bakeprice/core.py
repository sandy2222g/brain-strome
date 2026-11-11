"""Fit a demand curve to bake-sale history and pick the profit-maximising price.

Demand is modelled with constant elasticity, units = a * price^e, fitted by least squares on logs. For e < -1
profit (p - cost) * a * p^e is maximised at p* = cost * e / (1 + e). For e >= -1 profit keeps rising with price,
so we stop at the top of the prices actually tried. The answer is always kept inside the observed price range:
the data says nothing about prices outside it.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "sales.csv"
MIN_POINTS = 4


class PricingError(ValueError):
    """Invalid sales history."""


@dataclass(frozen=True)
class Sale:
    price: float
    units: int


@dataclass(frozen=True)
class Curve:
    a: float
    elasticity: float
    r2: float
    low: float
    high: float

    def units(self, price: float) -> float:
        return self.a * price**self.elasticity


def load(path: Path = DATA) -> dict[str, tuple[float, list[Sale]]]:
    out: dict[str, tuple[float, list[Sale]]] = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            cost, sales = out.setdefault(row["item"], (float(row["unit_cost"]), []))
            sales.append(Sale(float(row["price"]), int(row["units"])))
    return out


def fit(sales: list[Sale]) -> Curve:
    if len(sales) < MIN_POINTS:
        raise PricingError(f"need at least {MIN_POINTS} observations")
    if any(s.price <= 0 or s.units <= 0 for s in sales):
        raise PricingError("prices and units must be positive")
    xs = [math.log(s.price) for s in sales]
    ys = [math.log(s.units) for s in sales]
    if max(xs) - min(xs) < 1e-9:
        raise PricingError("need at least two different prices")
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    intercept = my - slope * mx
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    ss_tot = sum((y - my) ** 2 for y in ys) or 1.0
    return Curve(
        math.exp(intercept), slope, 1 - ss_res / ss_tot, min(s.price for s in sales), max(s.price for s in sales)
    )


def profit(curve: Curve, cost: float, price: float) -> float:
    return (price - cost) * curve.units(price)


def best_price(curve: Curve, cost: float) -> float:
    if cost <= 0:
        raise PricingError("unit cost must be positive")
    e = curve.elasticity
    raw = curve.high if e >= -1 else cost * e / (1 + e)
    return round(min(max(raw, curve.low), curve.high), 2)


def cost_plus_price(curve: Curve, cost: float, markup: float = 1.0) -> float:
    """Baseline rule of thumb: charge cost plus 100% (double the cost), kept inside the tried range."""
    return round(min(max(cost * (1 + markup), curve.low), curve.high), 2)
