"""FastAPI app for the plank cutting planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from plankcut.core import PlankError, best_cuts, build, load, single_size

ROOT = Path(__file__).resolve().parents[2]


class CutIn(BaseModel):
    length: int
    prices: dict[str, float]


app = FastAPI(title="Plank Cutting Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


def _fmt(plan: tuple[float, list[int]], length: int) -> dict[str, Any]:
    return {"value": plan[0], "pieces": plan[1], "waste": length - sum(plan[1])}


@app.post("/cut")
def cut(body: CutIn) -> dict[str, Any]:
    try:
        prices = build(body.prices, body.length)
    except (PlankError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    return {
        "length": body.length,
        "best": _fmt(best_cuts(prices, body.length), body.length),
        "single_size": _fmt(single_size(prices, body.length), body.length),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
