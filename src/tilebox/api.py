"""FastAPI app for the tile box calculator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tilebox.core import TileError, build, load, plan

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Tile Box Calculator", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/calc")
def calc(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        job = build(raw)
    except TileError as err:
        raise HTTPException(422, str(err)) from err
    straight = plan(build({**raw, "layout": "straight"}))
    diagonal = plan(build({**raw, "layout": "diagonal"}))
    return {"chosen": plan(job), "layout": job.layout, "straight": straight, "diagonal": diagonal}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
