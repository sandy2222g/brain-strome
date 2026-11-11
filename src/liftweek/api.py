"""FastAPI app for the weekly strength planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from liftweek.core import PlanError, load, plan

ROOT = Path(__file__).resolve().parents[2]


class PlanIn(BaseModel):
    exercises: list[str] = Field(min_length=1, max_length=30)
    days: int = Field(default=3, ge=1, le=7)
    minutes_per_day: int = Field(default=45, ge=10, le=180)


app = FastAPI(title="Gym Week Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/exercises")
def exercises() -> list[dict[str, Any]]:
    return [{"name": e.name, "muscles": list(e.muscles), "minutes": e.minutes} for e in load().values()]


@app.post("/plan")
def make(body: PlanIn) -> dict[str, Any]:
    try:
        return plan(body.exercises, body.days, body.minutes_per_day)
    except PlanError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
