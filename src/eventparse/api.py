"""FastAPI app for the quick event parser."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from eventparse.core import ParseError, load, parse

ROOT = Path(__file__).resolve().parents[2]


class ParseIn(BaseModel):
    sentences: list[str] = Field(min_length=1, max_length=100)
    today: str


app = FastAPI(title="Quick Event Parser", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/parse")
def parse_many(body: ParseIn) -> dict[str, Any]:
    try:
        today = date.fromisoformat(body.today)
        return {"events": [{"text": s, **parse(s, today)} for s in body.sentences]}
    except (ParseError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
