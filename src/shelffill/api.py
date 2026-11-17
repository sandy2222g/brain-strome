"""FastAPI app for the bookshelf filler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from shelffill.core import ShelfError, compare, load

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    shelf_width: float = Field(gt=0)
    books: list[dict[str, Any]] = Field(max_length=500)


app = FastAPI(title="Bookshelf Filler", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/fill")
def run(body: In) -> dict[str, Any]:
    try:
        return compare(body.books, body.shelf_width)
    except (ShelfError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
