"""FastAPI app for the Countdown solver."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import CountdownError, random_puzzle, solve

app = FastAPI(title="Countdown Solver")
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/solve")
def solve_it(numbers: str = Query(..., max_length=40), target: int = Query(..., ge=1, le=999)) -> dict[str, object]:
    try:
        nums = [int(x) for x in numbers.split(",")]
        return solve(nums, target)
    except (ValueError, CountdownError) as e:
        raise HTTPException(422, str(e)) from e


@app.get("/puzzle")
def puzzle(seed: int = Query(0, ge=0, le=10**6)) -> dict[str, object]:
    return random_puzzle(seed)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
