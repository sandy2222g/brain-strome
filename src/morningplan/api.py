"""FastAPI app for the morning routine planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from morningplan.core import RoutineError, load, wake_time

ROOT = Path(__file__).resolve().parents[2]


class RoutineIn(BaseModel):
    leave: str
    tasks: list[dict[str, Any]] = Field(max_length=100)


app = FastAPI(title="Morning Routine Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def plan(body: RoutineIn) -> dict[str, Any]:
    try:
        return wake_time(body.leave, body.tasks)
    except (RoutineError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
