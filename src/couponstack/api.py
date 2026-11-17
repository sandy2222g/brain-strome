"""FastAPI app for the coupon stack chooser."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from couponstack.core import CouponError, compare, load

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    subtotal: float = Field(ge=0)
    shipping: float = Field(ge=0)
    coupons: list[dict[str, Any]] = Field(max_length=30)


app = FastAPI(title="Coupon Stack Chooser", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/choose")
def run(body: In) -> dict[str, Any]:
    try:
        return compare(body.subtotal, body.shipping, body.coupons)
    except (CouponError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
