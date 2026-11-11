"""FastAPI app for the flashcard review scheduler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from recall.core import DATA, MAX_CARDS, Card, DeckError, build, compare

ROOT = Path(__file__).resolve().parents[2]


class CardIn(BaseModel):
    name: str = Field(max_length=60)
    hardness: float = Field(ge=0.5, le=3)


class CompareIn(BaseModel):
    cards: list[CardIn] = Field(min_length=1, max_length=MAX_CARDS)
    days: int = Field(default=60, ge=7, le=365)
    seeds: int = Field(default=40, ge=1, le=100)


app = FastAPI(title="Flashcard Review Scheduler", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/compare")
def compare_schedules(body: CompareIn) -> dict[str, Any]:
    try:
        cards, days = build([Card(c.name, c.hardness) for c in body.cards], body.days)
    except DeckError as err:
        raise HTTPException(422, str(err)) from err
    return {"days": days, "cards": len(cards), "strategies": compare(cards, days, body.seeds)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
