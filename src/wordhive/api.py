"""FastAPI app for the word hive solver."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from wordhive.core import HiveError, load, rank, solve

ROOT = Path(__file__).resolve().parents[2]


class SolveIn(BaseModel):
    letters: str
    center: str
    words: list[str] | None = Field(default=None, max_length=50000)


app = FastAPI(title="Word Hive Solver", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/solve")
def run(body: SolveIn) -> dict[str, Any]:
    words = body.words if body.words is not None else load()["words"]
    try:
        result = solve(words, body.letters, body.center)
    except HiveError as err:
        raise HTTPException(422, str(err)) from err
    result["ranks"] = {
        name: rank(int(result["total_points"] * share), result["total_points"])
        for name, share in (("quarter", 0.25), ("half", 0.5), ("most", 0.7))
    }
    return result


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
