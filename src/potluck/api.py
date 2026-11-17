"""FastAPI app for the potluck dish matcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from potluck.core import PotluckError, first_come, load, match

ROOT = Path(__file__).resolve().parents[2]


class PartyIn(BaseModel):
    needs: dict[str, int]
    guests: list[dict[str, Any]] = Field(max_length=200)


app = FastAPI(title="Potluck Dish Matcher", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/match")
def run(body: PartyIn) -> dict[str, Any]:
    try:
        return {"best": match(body.guests, body.needs), "first_come": first_come(body.guests, body.needs)}
    except (PotluckError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
