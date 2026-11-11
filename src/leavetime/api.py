"""FastAPI app for the commute leave-time planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from leavetime.core import LeaveError, fixed_buffer_rate, hhmm, leave_by, load, on_time_rate, predict_minutes, split

ROOT = Path(__file__).resolve().parents[2]
TRIPS = load()
TRAIN, TEST = split(TRIPS)


class PlanIn(BaseModel):
    arrive_hour: float = Field(ge=5, le=23)
    confidence: float = Field(default=0.9, gt=0.5, lt=0.999)


app = FastAPI(title="Commute Leave-Time Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    try:
        r = leave_by(TRAIN, body.arrive_hour, body.confidence)
        median = predict_minutes(TRAIN, r["leave_hour"], 0.5)
    except LeaveError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "leave_time": hhmm(r["leave_hour"]),
        "minutes_needed": r["minutes_needed"],
        "typical_minutes": round(median, 1),
        "buffer_minutes": round(r["minutes_needed"] - median, 1),
        "confidence": body.confidence,
    }


@app.get("/calibration")
def calibration() -> dict[str, Any]:
    levels = [0.5, 0.7, 0.8, 0.9, 0.95]
    return {
        "levels": [{"target": q, "actual": round(on_time_rate(TRAIN, TEST, q), 3)} for q in levels],
        "fixed_buffer_20pct": round(fixed_buffer_rate(TRAIN, TEST), 3),
        "train_trips": len(TRAIN),
        "test_trips": len(TEST),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
