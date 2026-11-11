"""FastAPI app for the laundry slot scheduler."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from washrota.core import RotaError, assign, first_come, summary

ROOT = Path(__file__).resolve().parents[2]


class RotaIn(BaseModel):
    slots: list[str] = Field(min_length=1, max_length=60)
    residents: dict[str, list[str]] = Field(min_length=1, max_length=60)


app = FastAPI(title="Laundry Slot Scheduler", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "sample_block.json").read_text())


@app.post("/assign")
def run(body: RotaIn) -> dict[str, Any]:
    try:
        best = assign(body.slots, body.residents)
        naive = first_come(body.slots, body.residents)
    except RotaError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "assignments": best,
        "summary": summary(body.residents, best),
        "first_come_summary": summary(body.residents, naive),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
