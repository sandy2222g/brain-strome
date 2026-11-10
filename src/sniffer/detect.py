"""Recurring-charge detection.

A merchant is a recurring charge when (1) it appears often enough, (2) the gaps between
charges cluster around a known billing period, and (3) the amounts are stable (or step
between a few stable levels). Irregular spending (groceries, coffee) fails (2) or (3).
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from sniffer.normalize import merchant_key

# name -> (period in days, allowed deviation in days, minimum charges)
PERIODS: dict[str, tuple[int, int, int]] = {
    "weekly": (7, 2, 4),
    "monthly": (30, 4, 3),
    "quarterly": (91, 7, 3),
    "yearly": (365, 12, 2),
}
MIN_REGULARITY = 0.8
AMOUNT_TOLERANCE = 0.10
HIKE_THRESHOLD = 0.03
DAYS_PER_MONTH = 30.44


@dataclass(frozen=True)
class Txn:
    day: date
    description: str
    amount: float  # negative = money out


@dataclass
class Hike:
    day: str
    old: float
    new: float


@dataclass
class Recurring:
    merchant: str
    cadence: str
    charges: int
    last_amount: float
    monthly_cost: float
    annual_cost: float
    first_seen: str
    last_seen: str
    next_expected: str
    active: bool
    confidence: float
    hikes: list[Hike] = field(default_factory=list)
    annual_hike_cost: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _cadence(intervals: list[int], n: int) -> tuple[str, float] | None:
    """Best matching billing period and the share of gaps that fit it."""
    best: tuple[str, float] | None = None
    for name, (period, tol, min_n) in PERIODS.items():
        if n < min_n:
            continue
        fit = sum(abs(i - period) <= tol for i in intervals) / len(intervals)
        if fit >= MIN_REGULARITY and (best is None or fit > best[1]):
            best = (name, fit)
    return best


def _amount_stability(amounts: list[float]) -> float:
    med = statistics.median(amounts)
    return sum(abs(a - med) / med <= AMOUNT_TOLERANCE for a in amounts) / len(amounts) if med else 0.0


def _hikes(days: list[date], amounts: list[float]) -> list[Hike]:
    """Persistent price steps. Only judged for fixed-price series (most gaps unchanged)."""
    diffs = [(b - a) / a for a, b in zip(amounts, amounts[1:], strict=False) if a]
    if not diffs or sum(abs(d) < 0.02 for d in diffs) / len(diffs) < 0.7:
        return []
    out: list[Hike] = []
    for i in range(1, len(amounts)):
        old, new = amounts[i - 1], amounts[i]
        if old and (new - old) / old >= HIKE_THRESHOLD:
            out.append(Hike(days[i].isoformat(), round(old, 2), round(new, 2)))
    return out


def detect(txns: list[Txn], today: date | None = None) -> list[Recurring]:
    """Find recurring outgoing payments. `today` defaults to the last transaction date."""
    spend = [t for t in txns if t.amount < 0]
    if not spend:
        return []
    end = today or max(t.day for t in txns)
    groups: dict[str, list[Txn]] = {}
    for t in spend:
        groups.setdefault(merchant_key(t.description), []).append(t)
    found: list[Recurring] = []
    for key, items in groups.items():
        items.sort(key=lambda t: t.day)
        days = [t.day for t in items]
        amounts = [-t.amount for t in items]
        if len(items) < 2:
            continue
        intervals = [(b - a).days for a, b in zip(days, days[1:], strict=False)]
        cad = _cadence(intervals, len(items))
        hikes = _hikes(days, amounts)
        if not cad or (_amount_stability(amounts) < 0.7 and not hikes):
            continue
        name, regularity = cad
        period = PERIODS[name][0]
        last = amounts[-1]
        per_year = 365.0 / period
        annual_hike = sum((h.new - h.old) * per_year for h in hikes)
        stability = _amount_stability(amounts)
        confidence = round(0.5 * regularity + 0.3 * stability + 0.2 * min(len(items) / 6, 1.0), 2)
        next_expected = days[-1] + timedelta(days=period)
        found.append(
            Recurring(
                merchant=key, cadence=name, charges=len(items), last_amount=round(last, 2),
                monthly_cost=round(last * per_year / 12, 2), annual_cost=round(last * per_year, 2),
                first_seen=days[0].isoformat(), last_seen=days[-1].isoformat(),
                next_expected=next_expected.isoformat(),
                active=(end - days[-1]).days <= period * 1.5,
                confidence=confidence, hikes=hikes, annual_hike_cost=round(annual_hike, 2),
            )
        )
    found.sort(key=lambda r: -r.annual_cost)
    return found
