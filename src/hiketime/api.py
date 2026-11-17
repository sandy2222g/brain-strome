"""FastAPI app for the hike time estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from hiketime.core import HikeError, estimate, load

ROOT = Path(__file__).resolve().parents[2]


class TrailIn(BaseModel):
    sunset: str
    pace_kmh: float = Field(default=5.0, gt=0, le=15)
    ascent_min_per_100m: float = Field(default=10.0, ge=0, le=60)
    rest_min_per_hour: float = Field(default=5.0, ge=0, le=30)
    points: list[dict[str, Any]] = Field(max_length=500)


app = FastAPI(title="Hike Time Estimator", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/estimate")
def make_estimate(body: TrailIn) -> dict[str, Any]:
    try:
        return estimate(body.model_dump())
    except (HikeError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
