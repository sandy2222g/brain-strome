"""FastAPI app for the book club picker."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from clubpick.core import VoteError, tally

ROOT = Path(__file__).resolve().parents[2]


class BallotIn(BaseModel):
    voter: str = Field(max_length=40)
    ranking: list[str] = Field(min_length=2, max_length=30)


class VoteIn(BaseModel):
    books: list[str] = Field(min_length=2, max_length=30)
    ballots: list[BallotIn] = Field(min_length=1, max_length=500)


app = FastAPI(title="Book Club Picker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "ballots.json").read_text())


@app.post("/tally")
def run(body: VoteIn) -> dict[str, Any]:
    try:
        return tally(body.books, [b.ranking for b in body.ballots])
    except VoteError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
