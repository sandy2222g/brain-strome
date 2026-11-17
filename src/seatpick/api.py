"""FastAPI app for the cinema seat picker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from seatpick.core import SeatError, best, first_free, load, mark

ROOT = Path(__file__).resolve().parents[2]


class PickIn(BaseModel):
    rows: list[str] = Field(max_length=60)
    party: int = Field(ge=1, le=20)


app = FastAPI(title="Cinema Seat Picker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/pick")
def pick(body: PickIn) -> dict[str, Any]:
    try:
        chosen = best(body.rows, body.party)
        naive = first_free(body.rows, body.party)
    except SeatError as err:
        raise HTTPException(422, str(err)) from err
    return {"best": chosen, "first_free": naive, "map": mark(body.rows, chosen), "naive_map": mark(body.rows, naive)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
