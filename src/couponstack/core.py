"""Find the coupon combination with the lowest checkout total (invented cart), in integer cents."""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "cart.json"
MAX_COUPONS = 14
KINDS = ("percent", "fixed", "shipping")


class CouponError(ValueError):
    """Raised for invalid input."""


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DATA.read_text())
    return data


def cents(x: float) -> int:
    return round(x * 100)


def _coupons(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(raw) > MAX_COUPONS:
        raise CouponError(f"at most {MAX_COUPONS} coupons")
    out = []
    for c in raw:
        if c["kind"] not in KINDS:
            raise CouponError(f"unknown coupon kind: {c['kind']}")
        if c["value"] < 0 or c["min_spend"] < 0 or (c["kind"] == "percent" and c["value"] > 100):
            raise CouponError(f"bad value in {c['code']}")
        out.append({**c, "max_off_c": cents(c["max_off"]) if c.get("max_off") else None})
    if len({c["code"] for c in out}) != len(out):
        raise CouponError("coupon codes must be unique")
    return out


def total_with(subtotal_c: int, shipping_c: int, chosen: list[dict[str, Any]]) -> dict[str, Any]:
    """Checkout total for one combination. Percent coupons first (each on the running price, capped),
    then fixed amounts, then free shipping. Minimum spend is judged on the original subtotal."""
    price = subtotal_c
    steps = []
    for c in sorted((c for c in chosen if c["kind"] == "percent"), key=lambda c: -c["value"]):
        off = (price * round(c["value"] * 100) + 5000) // 10000  # half-up, value in hundredths of a percent
        if c["max_off_c"] is not None:
            off = min(off, c["max_off_c"])
        price -= off
        steps.append((c["code"], off))
    for c in (c for c in chosen if c["kind"] == "fixed"):
        off = min(price, cents(c["value"]))
        price -= off
        steps.append((c["code"], off))
    ship = shipping_c
    for c in (c for c in chosen if c["kind"] == "shipping"):
        steps.append((c["code"], ship))
        ship = 0
    return {"total_c": price + ship, "steps": steps}


def valid(combo: tuple[dict[str, Any], ...], subtotal_c: int) -> bool:
    groups = [c["group"] for c in combo]
    return len(set(groups)) == len(groups) and all(subtotal_c >= cents(c["min_spend"]) for c in combo)


def _report(subtotal_c: int, shipping_c: int, combo: list[dict[str, Any]]) -> dict[str, Any]:
    r = total_with(subtotal_c, shipping_c, combo)
    return {
        "coupons": [c["code"] for c in combo],
        "discounts": [{"code": code, "off": off / 100} for code, off in r["steps"]],
        "total": r["total_c"] / 100,
        "saved": (subtotal_c + shipping_c - r["total_c"]) / 100,
    }


def best(subtotal: float, shipping: float, raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Try every subset (at most 2^14), keep the valid one with the lowest total; ties prefer fewer coupons."""
    if subtotal < 0 or shipping < 0:
        raise CouponError("subtotal and shipping cannot be negative")
    s, sh, coupons = cents(subtotal), cents(shipping), _coupons(raw)
    winner: tuple[int, int, list[dict[str, Any]]] = (s + sh, 0, [])
    for r in range(1, len(coupons) + 1):
        for combo in itertools.combinations(coupons, r):
            if not valid(combo, s):
                continue
            t = total_with(s, sh, list(combo))["total_c"]
            if (t, r) < winner[:2]:
                winner = (t, r, list(combo))
    return _report(s, sh, winner[2])


def best_single_percent(subtotal: float, shipping: float, raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Baseline: use only the coupon with the biggest headline percentage that the cart qualifies for."""
    s, sh, coupons = cents(subtotal), cents(shipping), _coupons(raw)
    ok = [c for c in coupons if c["kind"] == "percent" and s >= cents(c["min_spend"])]
    pick = [max(ok, key=lambda c: c["value"])] if ok else []
    return _report(s, sh, pick)


def compare(subtotal: float, shipping: float, raw: list[dict[str, Any]]) -> dict[str, Any]:
    b, n = best(subtotal, shipping, raw), best_single_percent(subtotal, shipping, raw)
    return {"best": b, "baseline": n, "extra_saved": round(n["total"] - b["total"], 2)}
