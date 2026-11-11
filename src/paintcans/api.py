"""FastAPI app for the paint can planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from paintcans.core import (
    MAX_ROOMS,
    PaintError,
    Room,
    baseline_largest,
    baseline_smallest,
    cheapest_cans,
    litres_needed,
    load,
)

ROOT = Path(__file__).resolve().parents[2]


class RoomIn(BaseModel):
    name: str = Field(max_length=40)
    width: float = Field(gt=0, le=50)
    length: float = Field(gt=0, le=50)
    height: float = Field(gt=0, le=10)
    openings: float = Field(default=0, ge=0, le=200)


class JobIn(BaseModel):
    coats: int
    coverage: float
    cans: dict[str, float]
    rooms: list[RoomIn] = Field(min_length=1, max_length=MAX_ROOMS)


app = FastAPI(title="Paint Can Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


def _fmt(plan: tuple[float, dict[float, int]]) -> dict[str, Any]:
    return {"cost": plan[0], "cans": {str(k): v for k, v in plan[1].items()}}


@app.post("/plan")
def plan(job: JobIn) -> dict[str, Any]:
    try:
        cans = {float(k): v for k, v in job.cans.items()}
        litres = litres_needed([Room(**r.model_dump()) for r in job.rooms], job.coats, job.coverage)
        return {
            "litres": round(litres, 2),
            "optimal": _fmt(cheapest_cans(litres, cans)),
            "largest_only": _fmt(baseline_largest(litres, cans)),
            "smallest_only": _fmt(baseline_smallest(litres, cans)),
        }
    except (PaintError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
