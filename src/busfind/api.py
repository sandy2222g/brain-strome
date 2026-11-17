"""FastAPI app for the next bus finder."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from busfind.core import BusError, board, load

ROOT = Path(__file__).resolve().parents[2]


class BoardIn(BaseModel):
    routes: list[dict[str, Any]]
    now: str
    walk_min: int = Field(default=0, ge=0, le=120)


app = FastAPI(title="Next Bus Finder", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/board")
def get_board(body: BoardIn) -> dict[str, Any]:
    try:
        rows = board(body.routes, body.now, body.walk_min)
    except (BusError, KeyError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    return {"rows": rows}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
