"""FastAPI app for the dinner sync planner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dinnersync.core import (
    DATA,
    MealError,
    Slot,
    Step,
    peak_usage,
    sequential_schedule,
    span,
    sync_schedule,
    waiting_minutes,
)

ROOT = Path(__file__).resolve().parents[2]


class StepIn(BaseModel):
    step: str = Field(max_length=60)
    minutes: int = Field(gt=0, le=300)
    resource: str = Field(max_length=20)


class DishIn(BaseModel):
    name: str = Field(max_length=40)
    steps: list[StepIn] = Field(min_length=1, max_length=10)


class MealIn(BaseModel):
    capacity: dict[str, int]
    dishes: list[DishIn] = Field(min_length=1, max_length=12)


app = FastAPI(title="Dinner Sync Planner", version="1.0.0")


def _rows(slots: list[Slot]) -> list[dict[str, Any]]:
    return [{"dish": s.dish, "step": s.step, "resource": s.resource, "start": s.start, "end": s.end} for s in slots]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text()) | {"name": "Sunday roast"}


@app.post("/plan")
def plan(body: MealIn) -> dict[str, Any]:
    dishes = [[Step(d.name, s.step, s.minutes, s.resource) for s in d.steps] for d in body.dishes]
    try:
        synced = sync_schedule(body.capacity, dishes)
        naive = sequential_schedule(body.capacity, dishes)
    except MealError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "synced": {"slots": _rows(synced), "span": span(synced), "waiting": waiting_minutes(synced)},
        "sequential": {"slots": _rows(naive), "span": span(naive), "waiting": waiting_minutes(naive)},
        "peak": {r: peak_usage(synced, r) for r in body.capacity},
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
