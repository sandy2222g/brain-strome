"""FastAPI app for the sudoku coach."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sudokucoach.core import SudokuError, count_solutions, find_hint, fmt, generate, parse, rate, solve

ROOT = Path(__file__).resolve().parents[2]


class GridIn(BaseModel):
    grid: str = Field(min_length=81, max_length=100)


app = FastAPI(title="Sudoku Coach", version="1.0.0")


def _grid(body: GridIn) -> list[int]:
    try:
        return parse(body.grid)
    except SudokuError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/puzzle")
def puzzle(
    seed: int = Query(default=1, ge=0, le=10**9), clues: int = Query(default=34, ge=17, le=81)
) -> dict[str, Any]:
    g = generate(seed, clues)
    return {"seed": seed, "grid": fmt(g), "clues": 81 - g.count(0), "difficulty": rate(g)}


@app.post("/hint")
def hint(body: GridIn) -> dict[str, Any]:
    g = _grid(body)
    if 0 not in g:
        return {"done": True}
    h = find_hint(g)
    if h is None:
        return {
            "done": False,
            "hint": None,
            "message": "No single is available: this step needs a guess or a harder technique.",
        }
    return {
        "done": False,
        "hint": {"cell": h.cell, "digit": h.digit, "technique": h.technique, "reason": h.reason},
    }


@app.post("/solve")
def solve_it(body: GridIn) -> dict[str, Any]:
    g = _grid(body)
    n = count_solutions(g[:], 2)
    sol = solve(g[:])
    return {"solvable": sol is not None, "unique": n == 1, "solution": fmt(sol) if sol else None}


@app.post("/check")
def check(body: GridIn) -> dict[str, Any]:
    g = _grid(body)
    sol = solve(g[:])
    return {"solvable": sol is not None, "complete": 0 not in g and sol is not None}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
