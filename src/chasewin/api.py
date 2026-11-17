"""FastAPI app for the chase win estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chasewin.core import ChaseError, analyse, load

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    preset: str = "balanced"
    target: int = Field(ge=1, le=600)
    runs: int = Field(ge=0, le=600)
    wickets: int = Field(ge=0, le=10)
    balls_left: int = Field(ge=0, le=300)
    total_balls: int = Field(default=120, ge=1, le=300)


app = FastAPI(title="Chase Win Estimator", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/estimate")
def run(body: In) -> dict[str, Any]:
    try:
        return analyse(body.preset, body.target, body.runs, body.wickets, body.balls_left, body.total_balls)
    except ChaseError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
