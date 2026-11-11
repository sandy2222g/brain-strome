"""FastAPI app for the road trip stop planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tripstops.core import TripError, load, naive_plan, plan, summary

ROOT = Path(__file__).resolve().parents[2]


class TripIn(BaseModel):
    range_km: float = Field(default=220, gt=20, le=1500)
    max_leg_km: float = Field(default=130, gt=20, le=600)


app = FastAPI(title="Road Trip Stop Planner", version="1.0.0")


def _row(s: Any) -> dict[str, Any]:
    return {"name": s.name, "km": s.km, "kind": s.kind, "price": s.price}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/route")
def route() -> dict[str, Any]:
    length, stops = load()
    return {"length_km": length, "stops": [_row(s) for s in stops]}


@app.post("/plan")
def make(body: TripIn) -> dict[str, Any]:
    length, stops = load()
    try:
        best = plan(length, stops, body.range_km, body.max_leg_km)
        naive = naive_plan(length, stops, body.range_km, body.max_leg_km)
    except TripError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "length_km": length,
        "stops": [_row(s) for s in best],
        "summary": summary(best),
        "naive_summary": summary(naive),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
