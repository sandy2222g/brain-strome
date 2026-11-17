"""FastAPI app for the sleep cycle planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sleepcycle.core import SleepError, bedtimes, eight_hour_bed, fixed_hours_check, load

ROOT = Path(__file__).resolve().parents[2]


class PlanIn(BaseModel):
    wake: str
    latency_min: int = Field(default=15, ge=0, le=120)
    cycle_min: int = Field(default=90, ge=60, le=120)


app = FastAPI(title="Sleep Cycle Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    try:
        options = bedtimes(body.wake, body.latency_min, body.cycle_min)
        naive = eight_hour_bed(body.wake)
        check = fixed_hours_check(naive, body.wake, 8.0, body.latency_min, body.cycle_min)
    except SleepError as err:
        raise HTTPException(422, str(err)) from err
    return {"options": options, "eight_hour_bed": naive, "eight_hour_check": check}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
