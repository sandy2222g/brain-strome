"""FastAPI app for the day timebox planner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from timebox.core import (
    DATA,
    Event,
    PlanError,
    Task,
    best_plan,
    free_gaps,
    hhmm,
    in_order_plan,
    total_priority,
)

ROOT = Path(__file__).resolve().parents[2]


class EventIn(BaseModel):
    title: str = Field(max_length=60)
    start: float = Field(ge=0, le=24)
    end: float = Field(ge=0, le=24)


class TaskIn(BaseModel):
    title: str = Field(max_length=60)
    minutes: int = Field(gt=0, le=480)
    priority: int = Field(ge=1, le=5)
    deadline: float | None = Field(default=None, ge=0, le=24)


class DayIn(BaseModel):
    day_start: float = Field(default=9.0, ge=0, le=23)
    day_end: float = Field(default=18.0, gt=0, le=24)
    buffer_min: int = Field(default=5, ge=0, le=30)
    events: list[EventIn] = Field(default_factory=list, max_length=30)
    tasks: list[TaskIn] = Field(min_length=1, max_length=14)


app = FastAPI(title="Day Timebox Planner", version="1.0.0")


def _rows(plan: list[Any]) -> list[dict[str, Any]]:
    return [{"title": p.title, "start": hhmm(p.start), "end": hhmm(p.end), "priority": p.priority} for p in plan]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/plan")
def make(body: DayIn) -> dict[str, Any]:
    events = [Event(e.title, e.start, e.end) for e in body.events]
    tasks = [Task(t.title, t.minutes, t.priority, t.deadline) for t in body.tasks]
    try:
        gaps = free_gaps(body.day_start, body.day_end, events)
        best = best_plan(tasks, gaps, body.buffer_min)
        naive = in_order_plan(tasks, gaps, body.buffer_min)
    except PlanError as err:
        raise HTTPException(422, str(err)) from err
    scheduled = {p.title for p in best}
    return {
        "gaps": [{"start": hhmm(a), "end": hhmm(b)} for a, b in gaps],
        "plan": _rows(best),
        "dropped": [t.title for t in tasks if t.title not in scheduled],
        "priority": total_priority(best),
        "in_order_priority": total_priority(naive),
        "in_order_count": len(naive),
        "free_hours": round(sum(b - a for a, b in gaps), 2),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
