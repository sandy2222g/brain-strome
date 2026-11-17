"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import core

app = FastAPI(title="Elo Rating League")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/leaderboard")
def leaderboard() -> dict[str, object]:
    return {"players": core.leaderboard()}


@app.get("/evaluation")
def evaluation() -> dict[str, object]:
    return core.evaluate()


@app.get("/predict")
def predict(a: str, b: str) -> dict[str, object]:
    try:
        return core.predict(a, b)
    except core.LeagueError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
