"""FastAPI app for the birthday countdown."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bdaycount.core import BirthdayError, calendar_order, load, parse, upcoming

ROOT = Path(__file__).resolve().parents[2]


class ListIn(BaseModel):
    today: str
    people: list[dict[str, str]] = Field(min_length=1, max_length=200)


app = FastAPI(title="Birthday Countdown", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/upcoming")
def get_upcoming(body: ListIn) -> dict[str, Any]:
    try:
        rows = upcoming(body.people, parse(body.today))
        order = calendar_order(body.people)
    except (BirthdayError, KeyError) as err:
        raise HTTPException(422, str(err)) from err
    return {"rows": rows, "calendar_order": order}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
