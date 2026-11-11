"""FastAPI app for the moving-box packer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from boxpack.core import (
    DATA,
    MAX_EXACT_ITEMS,
    Box,
    Item,
    PackError,
    first_fit_decreasing,
    lower_bound,
    next_fit,
    optimal,
)

ROOT = Path(__file__).resolve().parents[2]


class ItemIn(BaseModel):
    name: str = Field(max_length=40)
    kg: float = Field(gt=0, le=1000)
    litres: float = Field(gt=0, le=5000)


class PackIn(BaseModel):
    box_kg: float = Field(gt=0, le=1000)
    box_litres: float = Field(gt=0, le=5000)
    items: list[ItemIn] = Field(min_length=1, max_length=MAX_EXACT_ITEMS)


app = FastAPI(title="Moving Box Packer", version="1.0.0")


def _rows(boxes: list[Box]) -> list[dict[str, Any]]:
    return [{"kg": b.kg, "litres": b.litres, "items": [i.name for i in b.items]} for b in boxes]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/pack")
def pack(body: PackIn) -> dict[str, Any]:
    items = [Item(i.name, i.kg, i.litres) for i in body.items]
    try:
        naive = next_fit(body.box_kg, body.box_litres, items)
        heur = first_fit_decreasing(body.box_kg, body.box_litres, items)
        best, proved = optimal(body.box_kg, body.box_litres, items)
    except PackError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "next_fit": _rows(naive),
        "first_fit_decreasing": _rows(heur),
        "optimal": _rows(best),
        "proved_optimal": proved,
        "lower_bound": lower_bound(body.box_kg, body.box_litres, items),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
