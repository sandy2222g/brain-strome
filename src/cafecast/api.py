"""FastAPI app for the cafe demand forecaster."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cafecast.core import ForecastError, evaluate, load, plan_bakes

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    last_day: date
    sold: list[float] = Field(min_length=1, max_length=730)
    days: int = Field(default=7, ge=1, le=28)


app = FastAPI(title="Cafe Demand Forecaster", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/evaluation")
def evaluation() -> dict[str, Any]:
    return evaluate()


@app.get("/sample")
def sample() -> dict[str, Any]:
    dates, y = load()
    return {"last_day": dates[-1].isoformat(), "sold": y}


@app.post("/plan")
def run(body: In) -> dict[str, Any]:
    try:
        return plan_bakes(body.sold, body.last_day, body.days)
    except ForecastError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
