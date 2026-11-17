"""FastAPI app for the unbeatable tic-tac-toe."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import GameError, best_move, count_nodes, moves, play, turn, validate, winner

app = FastAPI(title="Tic-tac-toe Minimax")
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/move")
def move(board: str = Query(..., min_length=9, max_length=9)) -> dict[str, object]:
    """Play one human move is done by the client; this returns the computer's reply and the new state."""
    try:
        validate(board)
        if winner(board) or not moves(board):
            return {"board": board, "winner": winner(board), "done": True, "move": None}
        m = best_move(board)
        nb = play(board, m)
    except GameError as e:
        raise HTTPException(422, str(e)) from e
    return {"board": nb, "move": m, "winner": winner(nb), "done": bool(winner(nb) or not moves(nb)), "turn": turn(nb)}


_STATS: dict[str, int] = {}


@app.get("/stats")
def stats() -> dict[str, int]:
    if not _STATS:
        _STATS.update(count_nodes())
    return dict(_STATS)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
