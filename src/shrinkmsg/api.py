"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Message Shrinker")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Text(BaseModel):
    text: str


class Packed(BaseModel):
    table: dict[str, str]
    bits: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/samples")
def samples() -> dict[str, object]:
    return {"samples": core.samples(), "evaluation": core.evaluate()}


@app.post("/shrink")
def shrink(t: Text) -> dict[str, object]:
    try:
        return core.shrink(t.text)
    except core.CodingError as e:
        raise HTTPException(422, str(e)) from e


@app.post("/expand")
def expand(p: Packed) -> dict[str, str]:
    try:
        return {"text": core.decode(p.bits, p.table)}
    except core.CodingError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
