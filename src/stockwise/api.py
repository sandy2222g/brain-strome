"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import core

app = FastAPI(title="Kitchen Stock Reorder")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/evaluation")
def evaluation(service: float = 0.95) -> dict[str, object]:
    try:
        return core.evaluate(service)
    except core.StockError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
