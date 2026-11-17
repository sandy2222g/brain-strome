"""FastAPI app for the photo album grouper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from albumgroup.core import AlbumError, group_by_day, group_by_gap, load

ROOT = Path(__file__).resolve().parents[2]


class GroupIn(BaseModel):
    photos: list[dict[str, str]] = Field(max_length=5000)
    gap_hours: float = Field(default=4, gt=0, le=240)


app = FastAPI(title="Photo Album Grouper", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/group")
def group(body: GroupIn) -> dict[str, Any]:
    try:
        albums = group_by_gap(body.photos, body.gap_hours)
        by_day = group_by_day(body.photos)
    except AlbumError as err:
        raise HTTPException(422, str(err)) from err
    return {"albums": albums, "by_day_count": len(by_day)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
