"""FastAPI app for the golden hour planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from goldenhour.core import SunError, load, plan, rule_of_thumb

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    date: str
    lat: float
    lon: float
    tz: float


app = FastAPI(title="Golden Hour Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def run(body: In) -> dict[str, Any]:
    try:
        return {"plan": plan(body.date, body.lat, body.lon, body.tz),
                "rule_of_thumb": rule_of_thumb(body.date, body.lat, body.lon, body.tz)}
    except SunError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
