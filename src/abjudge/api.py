"""FastAPI app for the A/B test judge."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import ABError, analyse, false_positive_rate, sample_size

app = FastAPI(title="A/B Test Judge")
STATIC = Path(__file__).resolve().parents[2] / "static"


class Test(BaseModel):
    conv_a: int = Field(ge=0)
    n_a: int = Field(ge=1)
    conv_b: int = Field(ge=0)
    n_b: int = Field(ge=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyse")
def run(t: Test) -> dict[str, object]:
    try:
        return dict(analyse(t.conv_a, t.n_a, t.conv_b, t.n_b))
    except ABError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/sample-size")
def size(base_rate: float = Query(..., gt=0, lt=1), min_lift: float = Query(..., gt=0, lt=1)) -> dict[str, int]:
    try:
        return {"per_variant": sample_size(base_rate, min_lift)}
    except ABError as e:
        raise HTTPException(422, str(e)) from e


_PEEK: dict[int, float] = {}


@app.get("/peeking")
def peeking() -> dict[str, object]:
    for k in (1, 5, 10):
        _PEEK.setdefault(k, false_positive_rate(k, trials=600))
    return {"rates": {str(k): v for k, v in _PEEK.items()}}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
