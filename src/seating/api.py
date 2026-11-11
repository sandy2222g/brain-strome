"""FastAPI app for the table seating planner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from seating.core import DATA, MAX_GUESTS, SeatingError, build, in_order, pairs_together, plan, score

ROOT = Path(__file__).resolve().parents[2]


class SeatIn(BaseModel):
    guests: list[str] = Field(min_length=1, max_length=MAX_GUESTS)
    likes: list[list[str]] = []
    feuds: list[list[str]] = []
    tables: int = Field(ge=1, le=20)
    seats: int = Field(ge=1, le=20)


app = FastAPI(title="Table Seating Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/seat")
def seat(body: SeatIn) -> dict[str, Any]:
    try:
        party = build(body.guests, body.likes, body.feuds, body.tables, body.seats)
    except SeatingError as err:
        raise HTTPException(422, str(err)) from err
    out: dict[str, Any] = {"likes_total": len(party.likes), "feuds_total": len(party.feuds)}
    for key, seating in (("in_order", in_order(party)), ("planned", plan(party))):
        out[key] = {
            "tables": seating,
            "score": score(party, seating),
            "likes_together": pairs_together(party, seating, "likes"),
            "feuds_together": pairs_together(party, seating, "feuds"),
        }
    return out


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
