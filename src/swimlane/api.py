"""FastAPI app for the swim lane assigner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from swimlane.core import LaneError, compare, load

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    lanes: int = Field(ge=1, le=20)
    capacity: int = Field(ge=1, le=20)
    swimmers: list[dict[str, Any]] = Field(max_length=200)


app = FastAPI(title="Swim Lane Assigner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/assign")
def run(body: In) -> dict[str, Any]:
    try:
        return compare(body.swimmers, body.lanes, body.capacity)
    except (LaneError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
