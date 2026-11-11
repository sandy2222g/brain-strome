"""FastAPI app for the race pace planner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pacer.core import (
    DATA,
    MAX_SEGMENTS,
    CourseError,
    Segment,
    budget_for_even_speed,
    build,
    effort,
    even_plan,
    optimal_plan,
    total_hours,
)

ROOT = Path(__file__).resolve().parents[2]


class SegmentIn(BaseModel):
    km: float = Field(gt=0, le=100)
    grade: float = Field(ge=-30, le=30)


class PlanIn(BaseModel):
    segments: list[SegmentIn] = Field(min_length=1, max_length=MAX_SEGMENTS)
    even_kmh: float = Field(gt=0, le=40)


app = FastAPI(title="Race Pace Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    try:
        segments, even_kmh = build([Segment(s.km, s.grade) for s in body.segments], body.even_kmh)
    except CourseError as err:
        raise HTTPException(422, str(err)) from err
    budget = budget_for_even_speed(segments, even_kmh)
    out: dict[str, Any] = {"segments": [{"km": s.km, "grade": s.grade} for s in segments]}
    for key, speeds in (("even", even_plan(segments, budget)), ("optimal", optimal_plan(segments, budget))):
        out[key] = {
            "speeds_kmh": [round(v, 2) for v in speeds],
            "minutes": round(total_hours(segments, speeds) * 60, 2),
            "effort_used": round(effort(segments, speeds) / budget, 4),
        }
    out["seconds_saved"] = round((out["even"]["minutes"] - out["optimal"]["minutes"]) * 60)
    return out


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
