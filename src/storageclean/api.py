"""FastAPI app for the storage cleanup picker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from storageclean.core import CleanError, compare, load

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    target_mb: int = Field(gt=0, le=2_000_000)
    items: list[dict[str, Any]] = Field(max_length=200)


app = FastAPI(title="Storage Cleanup Picker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/pick")
def run(body: In) -> dict[str, Any]:
    try:
        return compare(body.items, body.target_mb)
    except (CleanError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
