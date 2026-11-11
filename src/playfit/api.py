"""FastAPI app for the playlist fitter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from playfit.core import PlaylistError, Song, best_fit, build, in_order, load, total

ROOT = Path(__file__).resolve().parents[2]


class FitIn(BaseModel):
    target_minutes: int
    songs: list[dict[str, Any]]


app = FastAPI(title="Playlist Fitter", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


def _fmt(songs: list[Song]) -> dict[str, Any]:
    return {"seconds": total(songs), "songs": [{"title": s.title, "seconds": s.seconds} for s in songs]}


@app.post("/fit")
def fit(body: FitIn) -> dict[str, Any]:
    try:
        songs, target = build(body.songs, body.target_minutes)
    except (PlaylistError, KeyError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    return {"target": target, "best": _fmt(best_fit(songs, target)), "in_order": _fmt(in_order(songs, target))}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
