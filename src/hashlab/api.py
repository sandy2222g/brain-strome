"""FastAPI app for the hash table lab."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import curves

app = FastAPI(title="Hash Table Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"
LOADS = [0.1, 0.3, 0.5, 0.7, 0.8, 0.9]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_CACHE: dict[str, object] = {}


@app.get("/curves")
def get_curves() -> dict[str, object]:
    if not _CACHE:
        _CACHE.update({"loads": LOADS, "curves": curves(LOADS)})
    return dict(_CACHE)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
