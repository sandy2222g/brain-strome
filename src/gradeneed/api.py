"""FastAPI app for the final grade calculator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from gradeneed.core import GradeError, analyse, load, naive_mean

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    bands: dict[str, float]
    categories: list[dict[str, Any]] = Field(max_length=30)


app = FastAPI(title="Final Grade Needed", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/analyse")
def run(body: In) -> dict[str, Any]:
    try:
        out = analyse(body.categories, body.bands)
        out["naive_mean"] = naive_mean(body.categories)
        return out
    except (GradeError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
