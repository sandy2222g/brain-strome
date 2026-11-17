"""FastAPI app for the fair teams picker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from teampick.core import TeamError, broken_rules, load, split, top_two_picks

ROOT = Path(__file__).resolve().parents[2]


class SplitIn(BaseModel):
    players: list[dict[str, Any]] = Field(max_length=40)
    keep_apart: list[list[str]] = []
    keep_together: list[list[str]] = []


app = FastAPI(title="Fair Teams Picker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/split")
def make_split(body: SplitIn) -> dict[str, Any]:
    try:
        best = split(body.players, body.keep_apart, body.keep_together)
        naive = top_two_picks(body.players)
    except (TeamError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err
    return {
        "best": best,
        "captains_pick": naive,
        "captains_broken_rules": broken_rules(naive, body.keep_apart, body.keep_together),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
