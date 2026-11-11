"""FastAPI app for the Secret Santa draw."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from santadraw.core import DrawError, count_draws, draw

ROOT = Path(__file__).resolve().parents[2]


class DrawIn(BaseModel):
    names: list[str] = Field(min_length=3, max_length=60)
    exclusions: list[tuple[str, str]] = Field(default_factory=list)
    last_year: dict[str, str] = Field(default_factory=dict)
    seed: int | None = None


app = FastAPI(title="Secret Santa Matcher", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "sample_group.json").read_text())


@app.post("/draw")
def run(body: DrawIn) -> dict[str, Any]:
    try:
        result = draw(body.names, body.exclusions, body.last_year, body.seed)
        ways = count_draws(body.names, body.exclusions, body.last_year) if len(body.names) <= 12 else None
    except DrawError as err:
        raise HTTPException(422, str(err)) from err
    return {"assignments": result, "possible_draws": ways}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
