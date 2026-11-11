"""FastAPI app for the tip pool splitter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tippool.core import TipError, build, largest_remainder, load, naive_rounding

ROOT = Path(__file__).resolve().parents[2]


class PoolIn(BaseModel):
    pool_cents: int
    workers: list[dict[str, Any]]


app = FastAPI(title="Tip Pool Splitter", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/split")
def split(body: PoolIn) -> dict[str, Any]:
    try:
        workers = build(body.workers, body.pool_cents)
    except (TipError, KeyError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    fair, naive = largest_remainder(workers, body.pool_cents), naive_rounding(workers, body.pool_cents)
    return {
        "pool_cents": body.pool_cents,
        "fair": fair,
        "naive": naive,
        "fair_total": sum(fair.values()),
        "naive_total": sum(naive.values()),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
