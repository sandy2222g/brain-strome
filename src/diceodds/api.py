"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import core

app = FastAPI(title="Board Game Dice Odds")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/presets")
def presets() -> dict[str, object]:
    return {"presets": core.presets()}


@app.get("/odds")
def odds(expr: str, target: int | None = None) -> dict[str, object]:
    try:
        return core.analyse(expr, target)
    except core.DiceError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
