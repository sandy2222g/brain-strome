"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Elevator Dispatch Simulator")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Trip(BaseModel):
    time_s: int
    origin: int
    dest: int


class Scenario(BaseModel):
    trips: list[Trip] | None = None
    floors: int = 12
    capacity: int = 8


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, object]:
    return {"trips": [{"time_s": p.t, "origin": p.origin, "dest": p.dest} for p in core.load()]}


@app.post("/compare")
def compare(s: Scenario) -> dict[str, object]:
    try:
        people = [core.Person(t.time_s, t.origin, t.dest) for t in s.trips] if s.trips else None
        return {"results": core.compare(people, s.floors, s.capacity)}
    except core.LiftError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
