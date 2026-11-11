"""FastAPI app for the car park fee comparator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from parkfee.core import ParkError, build, cheapest, load

ROOT = Path(__file__).resolve().parents[2]


class CompareIn(BaseModel):
    carparks: list[dict[str, Any]]
    stays: list[int] = Field(min_length=1, max_length=20)


app = FastAPI(title="Car Park Fee Comparator", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/compare")
def compare(body: CompareIn) -> dict[str, Any]:
    try:
        cars = build(body.carparks)
        rows = []
        for m in body.stays:
            best, fees = cheapest(cars, m)
            rows.append({"minutes": m, "best": best, "fees": fees})
    except (ParkError, KeyError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    return {"rows": rows}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
