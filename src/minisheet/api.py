"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Mini Spreadsheet")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Cells(BaseModel):
    cells: dict[str, str]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, object]:
    return {"cells": core.sample()}


@app.post("/evaluate")
def evaluate(c: Cells) -> dict[str, object]:
    try:
        return core.evaluate(c.cells)
    except core.SheetError as e:
        raise HTTPException(422, e.code) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
