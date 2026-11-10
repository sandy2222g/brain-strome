"""FastAPI app: pick gear for a trip and see what each extra kilo buys."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from packlist.optimizer import Item, PackError, Trip, load_gear, optimise

ROOT = Path(__file__).resolve().parents[2]


class TripIn(BaseModel):
    days: int = Field(default=2, ge=1, le=14)
    people: int = Field(default=1, ge=1, le=8)
    min_temp_c: float = Field(default=8.0, ge=-20, le=35)
    rain_chance: float = Field(default=0.3, ge=0, le=1)
    sun: bool = True
    bugs: bool = False
    limit_kg: float = Field(default=9.0, ge=3, le=30)

    def to_trip(self) -> Trip:
        return Trip(**self.model_dump())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.gear = load_gear(ROOT / "data" / "gear.csv")
    yield


app = FastAPI(title="Trail Pack Optimizer", version="1.0.0", lifespan=lifespan)


def _item(i: Item) -> dict[str, Any]:
    return {
        "id": i.id,
        "name": i.name,
        "category": i.category,
        "weight_g": i.weight_g,
        "utility": i.utility,
        "required": i.required,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/gear")
def gear() -> list[dict[str, Any]]:
    return [_item(i) for i in app.state.gear]


@app.post("/pack")
def pack(body: TripIn) -> dict[str, Any]:
    trip = body.to_trip()
    try:
        p = optimise(app.state.gear, trip)
        curve = []
        for delta in (-2, -1, 0, 1, 2, 4):
            kg = trip.limit_kg + delta
            if 3 <= kg <= 30:
                q = optimise(app.state.gear, replace(trip, limit_kg=kg))
                curve.append({"limit_kg": kg, "utility": q.utility, "feasible": q.feasible})
    except PackError as exc:
        raise HTTPException(422, str(exc)) from exc
    cats: dict[str, int] = {}
    for i in p.chosen:
        cats[i.category] = cats.get(i.category, 0) + i.weight_g
    return {
        "chosen": [_item(i) for i in sorted(p.chosen, key=lambda i: (i.category, -i.weight_g))],
        "leave_behind": [_item(i) for i in p.leave_behind[:8]],
        "gear_g": p.gear_g,
        "food_g": p.food_g,
        "water_g": p.water_g,
        "total_g": p.total_g,
        "limit_g": p.limit_g,
        "utility": p.utility,
        "greedy_utility": p.greedy_utility,
        "feasible": p.feasible,
        "notes": p.notes,
        "by_category_g": cats,
        "curve": curve,
    }


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
