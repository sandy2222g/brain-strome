"""Plain-language verdict, negotiation hint and cheaper-alternatives search."""

from __future__ import annotations

from typing import Any

import pandas as pd

from rentcheck.config import CURRENCY, TARGET
from rentcheck.model import Range

FAIR_BAND_PCT = 10.0  # within this distance from the median counts as fair


def verdict(rent: float, r: Range) -> dict[str, Any]:
    """Compare a rent to the p10/p50/p90 range."""
    diff = (rent / r.p50 - 1) * 100
    if rent > r.p90 or diff > FAIR_BAND_PCT:
        label, key = "above market", "above"
    elif rent < r.p10 or diff < -FAIR_BAND_PCT:
        label, key = "below market", "below"
    else:
        label, key = "fair", "fair"
    pct = abs(round(diff))
    if key == "fair":
        where = f"{pct}% {'above' if diff >= 0 else 'below'}" if pct else "right at"
        sentence = f"This rent looks fair: {where} the typical price."
    elif key == "above":
        sentence = f"This rent is {pct}% above the market for a flat like this."
    else:
        sentence = f"This rent is {pct}% below the market for a flat like this."
    return {"key": key, "label": label, "diff_pct": round(diff, 1), "sentence": sentence}


def _money(x: float) -> str:
    return f"{CURRENCY}{x:,.0f}"


def negotiation_hint(rent: float, r: Range) -> str:
    v = verdict(rent, r)["key"]
    span = f"Comparable flats rent for {_money(r.p10)} to {_money(r.p90)}"
    if v == "above":
        ask = max(r.p50, r.p10)
        save = rent - ask
        return (
            f"{span}. Ask for about {_money(ask)} a month: that saves {_money(save)} a month, "
            f"{_money(save * 12)} a year. Point to the typical price and offer a longer lease."
        )
    if v == "fair":
        return (
            f"{span}. Your rent is in that range. Ask for a small extra instead of a lower price, "
            "such as a fixed rent for two years or a free repaint."
        )
    return (
        f"{span}. This rent is under the usual range, so it is a good deal. "
        "Check the lease and the condition of the flat, and avoid pushing the price down."
    )


def find_alternatives(
    listings: pd.DataFrame, listing: dict[str, Any], rent: float, limit: int = 6
) -> list[dict[str, Any]]:
    """Similar listings in other districts that cost less than ``rent``."""
    size = float(listing["size_m2"])
    pool = listings[
        (listings["district"] != listing["district"])
        & (listings["bedrooms"] == listing["bedrooms"])
        & (listings["size_m2"].between(size * 0.8, size * 1.2))
        & (listings[TARGET] < rent)
    ].copy()
    if pool.empty:
        return []
    pool["score"] = (
        (pool["size_m2"] - size).abs() / size
        + (pool["furnished"] != listing["furnished"]) * 0.15
        + (pool["balcony"] != listing["balcony"]) * 0.1
        + (pool["lift"] != listing["lift"]) * 0.1
        + (pool["dist_metro_km"] - listing["dist_metro_km"]).abs() * 0.08
        + (pool["dist_centre_km"] - listing["dist_centre_km"]).abs() * 0.02
        - (rent - pool[TARGET]) / rent * 0.6
    )
    top = pool.sort_values("score").head(limit)
    return [
        {
            "id": int(r.id),
            "district": str(r.district),
            "bedrooms": int(r.bedrooms),
            "size_m2": int(r.size_m2),
            "rent": int(r.rent),
            "saving": int(rent - r.rent),
            "dist_metro_km": float(r.dist_metro_km),
            "dist_centre_km": float(r.dist_centre_km),
            "furnished": bool(r.furnished),
            "balcony": bool(r.balcony),
            "lift": bool(r.lift),
        }
        for r in top.itertuples()
    ]
