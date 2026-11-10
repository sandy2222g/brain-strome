"""Turn detections into the numbers a person acts on."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sniffer.categorize import BILL_CATEGORIES, CategoryModel
from sniffer.detect import Txn, detect
from sniffer.normalize import merchant_key

# Categories where paying for two services is usually a choice worth questioning.
OVERLAP_CATEGORIES = {"streaming", "music", "news", "gaming", "fitness", "food"}


def monthly_totals(txns: list[Txn], keys: set[str]) -> list[dict[str, Any]]:
    """Spend per calendar month on the given merchant keys (for the monthly chart)."""
    totals: dict[str, float] = defaultdict(float)
    months: set[str] = set()
    for t in txns:
        months.add(t.day.strftime("%Y-%m"))
        if t.amount < 0 and merchant_key(t.description) in keys:
            totals[t.day.strftime("%Y-%m")] += -t.amount
    return [{"month": m, "amount": round(totals[m], 2)} for m in sorted(months)]


def analyze(txns: list[Txn], cats: CategoryModel, today: date | None = None) -> dict[str, Any]:
    found = detect(txns, today)
    items: list[dict[str, Any]] = []
    for r in found:
        d = r.to_dict()
        d["category"] = cats.predict(r.merchant)
        d["kind"] = "bill" if d["category"] in BILL_CATEGORIES else "subscription"
        items.append(d)
    subs = [i for i in items if i["kind"] == "subscription" and i["active"]]
    bills = [i for i in items if i["kind"] == "bill" and i["active"]]
    ended = [i for i in items if not i["active"]]
    by_cat: dict[str, list[str]] = defaultdict(list)
    for s in subs:
        by_cat[s["category"]].append(s["merchant"])
    overlaps = {c: m for c, m in by_cat.items() if len(m) > 1 and c in OVERLAP_CATEGORIES}
    keys = {i["merchant"] for i in subs}
    return {
        "transactions": len(txns),
        "subscriptions": subs,
        "bills": bills,
        "ended": ended,
        "monthly_subscriptions": round(sum(s["monthly_cost"] for s in subs), 2),
        "annual_subscriptions": round(sum(s["annual_cost"] for s in subs), 2),
        "monthly_bills": round(sum(b["monthly_cost"] for b in bills), 2),
        "price_hike_annual_cost": round(sum(s["annual_hike_cost"] for s in subs), 2),
        "overlaps": overlaps,
        "monthly_chart": monthly_totals(txns, keys),
    }

