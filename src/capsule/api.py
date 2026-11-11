"""FastAPI app for the carry-on capsule wardrobe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from capsule.core import (
    DATA,
    MAX_ITEMS,
    CapsuleError,
    Garment,
    best_capsule,
    lightest_first,
    outfits,
    pack_in_order,
    weight,
)

ROOT = Path(__file__).resolve().parents[2]


class GarmentIn(BaseModel):
    name: str = Field(max_length=40)
    kind: str
    style: str
    g: int = Field(gt=0, le=5000)


class CapsuleIn(BaseModel):
    limit_g: int = Field(gt=0, le=30000)
    items: list[GarmentIn] = Field(min_length=1, max_length=MAX_ITEMS)


app = FastAPI(title="Carry-on Capsule", version="1.0.0")


def _view(chosen: list[Garment]) -> dict[str, Any]:
    return {"outfits": outfits(chosen), "grams": weight(chosen), "items": [g.name for g in chosen]}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/capsule")
def capsule(body: CapsuleIn) -> dict[str, Any]:
    items = [Garment(i.name, i.kind, i.style, i.g) for i in body.items]
    try:
        return {
            "in_order": _view(pack_in_order(body.limit_g, items)),
            "lightest_first": _view(lightest_first(body.limit_g, items)),
            "best": _view(best_capsule(body.limit_g, items)),
        }
    except CapsuleError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
