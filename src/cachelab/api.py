"""FastAPI app for the cache policy lab."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import CacheError, curve

app = FastAPI(title="Cache Policy Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"
SIZES = [2, 5, 10, 20, 40, 80, 160]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/curve")
def hit_curve(kind: str = "zipf", seed: int = Query(0, ge=0, le=10**6)) -> dict[str, object]:
    try:
        return {"sizes": SIZES, "curves": curve(kind, SIZES, seed=seed)}
    except CacheError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
