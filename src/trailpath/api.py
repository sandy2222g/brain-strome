"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Terrain Trail Pathfinder")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Query(BaseModel):
    text: str
    algorithm: str = "astar"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/maps")
def maps() -> dict[str, object]:
    return {"maps": core.maps(), "evaluation": core.evaluate()}


@app.post("/solve")
def solve(q: Query) -> dict[str, object]:
    try:
        return core.solve(q.text, q.algorithm)
    except core.TrailError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
