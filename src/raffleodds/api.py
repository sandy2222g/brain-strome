"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import core

app = FastAPI(title="Raffle Ticket Reality Check")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/games")
def games() -> dict[str, object]:
    return {"games": [g.name for g in core.load_games()]}


@app.get("/analyse")
def analyse(game: int = 0, tickets: int = 520) -> dict[str, object]:
    try:
        return core.analyse(game, tickets)
    except core.OddsError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/raffle")
def raffle(tickets_sold: int, mine: int, prize: float, price: float) -> dict[str, float]:
    try:
        return core.raffle(tickets_sold, mine, prize, price)
    except core.OddsError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
