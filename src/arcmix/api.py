"""FastAPI app: build a playlist that follows an energy arc."""

from __future__ import annotations

from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from arcmix.builder import ARCS, PlaylistError, arc_at, build
from arcmix.library import Track, load_tracks

ROOT = Path(__file__).resolve().parents[2]


class BuildIn(BaseModel):
    arc: str | None = Field(default="Warm-up, peak, cool-down")
    points: list[tuple[float, float]] | None = Field(
        default=None, max_length=12, description="custom arc [(position, energy)]"
    )
    minutes: float = Field(default=45, ge=5, le=240)
    moods: list[str] | None = None
    seed: int = Field(default=0, ge=0, le=100000)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.tracks = load_tracks(ROOT / "data" / "tracks.csv")
    yield


app = FastAPI(title="Playlist Arc Builder", version="1.0.0", lifespan=lifespan)


def _track(t: Track) -> dict[str, Any]:
    return t.__dict__


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/arcs")
def arcs() -> dict[str, list[tuple[float, float]]]:
    return ARCS


@app.get("/moods")
def moods() -> dict[str, int]:
    return dict(Counter(t.mood for t in app.state.tracks))


@app.get("/tracks")
def tracks(limit: int = 50) -> list[dict[str, Any]]:
    return [_track(t) for t in app.state.tracks[: max(1, min(limit, 500))]]


@app.post("/build")
def build_playlist(body: BuildIn) -> dict[str, Any]:
    points = body.points or ARCS.get(body.arc or "")
    if points is None:
        raise HTTPException(422, f"unknown arc: {body.arc}")
    try:
        p = build(app.state.tracks, list(points), body.minutes, set(body.moods) if body.moods else None, seed=body.seed)
    except PlaylistError as exc:
        raise HTTPException(422, str(exc)) from exc
    total = body.minutes * 60.0
    elapsed, out = 0.0, []
    for s in p.steps:
        out.append(
            {
                **_track(s.track),
                "start_s": round(elapsed),
                "target_energy": round(s.target_energy, 3),
                "transition": round(s.transition, 3),
                "tempo_delta": round(s.tempo_delta, 1),
                "key_distance": round(s.key_distance, 2),
            }
        )
        elapsed += s.track.duration_s
    return {
        "tracks": out,
        "minutes": p.minutes,
        "arc_rmse": p.arc_rmse,
        "mean_transition": p.mean_transition,
        "baseline_arc_rmse": p.baseline_arc_rmse,
        "baseline_mean_transition": p.baseline_mean_transition,
        "arc": [{"x": i / 40, "y": round(arc_at(list(points), i / 40), 3)} for i in range(41)],
        "total_s": total,
    }


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
