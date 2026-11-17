"""FastAPI app for the bag weight balancer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bagbalance.core import BagError, alternate, balance, load, over_limit

ROOT = Path(__file__).resolve().parents[2]


class BalanceIn(BaseModel):
    items: list[dict[str, Any]] = Field(max_length=60)
    bag_limit_g: int = Field(default=23000, ge=1)


app = FastAPI(title="Bag Weight Balancer", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/balance")
def make_balance(body: BalanceIn) -> dict[str, Any]:
    try:
        best, alt = balance(body.items), alternate(body.items)
        return {
            "best": best,
            "alternating": alt,
            "best_over_limit": over_limit(best, body.bag_limit_g),
            "alternating_over_limit": over_limit(alt, body.bag_limit_g),
        }
    except (BagError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
