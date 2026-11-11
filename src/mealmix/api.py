"""FastAPI app for the meal prep budget mixer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mealmix.core import (
    DATA,
    MAX_FOODS,
    Food,
    MixError,
    Targets,
    best_mix,
    build,
    cheapest_per_kcal,
    meets,
    totals,
)

ROOT = Path(__file__).resolve().parents[2]


class FoodIn(BaseModel):
    name: str = Field(max_length=40)
    cost: float = Field(gt=0, le=1000)
    kcal: int = Field(gt=0, le=5000)
    protein: int = Field(ge=0, le=500)


class TargetsIn(BaseModel):
    kcal_min: int = Field(gt=0, le=10000)
    kcal_max: int = Field(gt=0, le=10000)
    protein_min: int = Field(ge=0, le=1000)


class MixIn(BaseModel):
    foods: list[FoodIn] = Field(min_length=1, max_length=MAX_FOODS)
    targets: TargetsIn
    max_servings: int = Field(default=4, ge=1, le=8)


app = FastAPI(title="Meal Prep Budget Mixer", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/mix")
def mix(body: MixIn) -> dict[str, Any]:
    try:
        foods, targets, cap = build(
            [Food(**f.model_dump()) for f in body.foods], Targets(**body.targets.model_dump()), body.max_servings
        )
        best = best_mix(foods, targets, cap)
    except MixError as err:
        raise HTTPException(422, str(err)) from err
    base = cheapest_per_kcal(foods, targets, cap)
    out: dict[str, Any] = {}
    for key, servings in (("baseline", base), ("best", best)):
        cost, kcal, protein = totals(foods, servings)
        out[key] = {
            "cost": cost,
            "kcal": kcal,
            "protein": protein,
            "meets_targets": meets(foods, targets, servings),
            "servings": {f.name: s for f, s in zip(foods, servings, strict=True) if s},
        }
    return out


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
