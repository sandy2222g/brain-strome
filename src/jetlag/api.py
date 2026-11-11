"""FastAPI app for the jet-lag planner."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import available_timezones

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jetlag.core import TripError, plan

ROOT = Path(__file__).resolve().parents[2]
POPULAR = [
    "Asia/Kolkata", "America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney",
    "America/Los_Angeles", "Europe/Paris", "Asia/Singapore", "Africa/Nairobi", "America/Sao_Paulo",
]  # fmt: skip


class TripIn(BaseModel):
    origin: str = Field(max_length=64)
    dest: str = Field(max_length=64)
    flight_day: date
    bed: float = Field(default=23.0, ge=0, lt=24)
    wake: float = Field(default=7.0, ge=0, lt=24)
    pre_days: int = Field(default=3, ge=0, le=7)


app = FastAPI(title="Jet Lag Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/zones")
def zones() -> dict[str, list[str]]:
    return {"popular": POPULAR, "all": sorted(z for z in available_timezones() if "/" in z and not z.startswith("Etc"))}


@app.post("/plan")
def make(body: TripIn) -> dict[str, Any]:
    try:
        return plan(body.origin, body.dest, body.flight_day, body.bed, body.wake, body.pre_days)
    except TripError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
