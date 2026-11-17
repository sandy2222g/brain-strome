"""FastAPI app for the unit price checker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from unitprice.core import PriceError, largest_pack, load, rank

ROOT = Path(__file__).resolve().parents[2]


class CompareIn(BaseModel):
    products: list[dict[str, Any]] = Field(max_length=100)


app = FastAPI(title="Unit Price Checker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/compare")
def compare(body: CompareIn) -> dict[str, Any]:
    try:
        rows = rank(body.products)
        biggest = largest_pack(body.products)
    except (PriceError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err
    return {"rows": rows, "best": rows[0]["name"], "largest": biggest}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
