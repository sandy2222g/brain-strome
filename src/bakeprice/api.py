"""FastAPI app for the bake sale pricer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bakeprice.core import DATA, PricingError, Sale, best_price, cost_plus_price, fit, load, profit

ROOT = Path(__file__).resolve().parents[2]


class SaleIn(BaseModel):
    price: float = Field(gt=0, le=1000)
    units: int = Field(gt=0, le=1_000_000)


class ItemIn(BaseModel):
    name: str = Field(max_length=40)
    unit_cost: float = Field(gt=0, le=1000)
    sales: list[SaleIn] = Field(min_length=1, max_length=500)


class PriceIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=30)


app = FastAPI(title="Bake Sale Pricer", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return {
        "items": [
            {"name": n, "unit_cost": cost, "sales": [{"price": s.price, "units": s.units} for s in sales]}
            for n, (cost, sales) in load(DATA).items()
        ]
    }


@app.post("/price")
def price(body: PriceIn) -> dict[str, Any]:
    out = []
    for item in body.items:
        try:
            curve = fit([Sale(s.price, s.units) for s in item.sales])
            best = best_price(curve, item.unit_cost)
        except PricingError as err:
            raise HTTPException(422, f"{item.name}: {err}") from err
        base = cost_plus_price(curve, item.unit_cost)
        out.append(
            {
                "name": item.name,
                "elasticity": round(curve.elasticity, 3),
                "r2": round(curve.r2, 3),
                "range": [curve.low, curve.high],
                "best_price": best,
                "baseline_price": base,
                "best_profit": round(profit(curve, item.unit_cost, best), 2),
                "baseline_profit": round(profit(curve, item.unit_cost, base), 2),
                "curve": [
                    {"price": round(p, 2), "units": round(curve.units(p), 1)}
                    for p in [curve.low + (curve.high - curve.low) * k / 24 for k in range(25)]
                ],
            }
        )
    return {"items": out}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
