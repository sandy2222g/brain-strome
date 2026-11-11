"""FastAPI app for the league fixture planner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from fixtures.core import (
    DATA,
    MAX_TEAMS,
    LeagueError,
    Round,
    build,
    circle_schedule,
    count_breaks,
    home_counts,
    naive_schedule,
)

ROOT = Path(__file__).resolve().parents[2]


class LeagueIn(BaseModel):
    name: str = Field(default="League", max_length=60)
    teams: list[str] = Field(min_length=2, max_length=MAX_TEAMS)


app = FastAPI(title="League Fixture Planner", version="1.0.0")


def _view(rounds: list[Round]) -> dict[str, Any]:
    homes = home_counts(rounds)
    return {
        "rounds": [[{"home": h, "away": a} for h, a in rd] for rd in rounds],
        "breaks": count_breaks(rounds),
        "home_games": homes,
        "home_spread": max(homes.values()) - min(homes.values()),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/schedule")
def schedule(body: LeagueIn) -> dict[str, Any]:
    try:
        league = build(body.name, body.teams)
    except LeagueError as err:
        raise HTTPException(422, str(err)) from err
    return {"name": league.name, "naive": _view(naive_schedule(league)), "balanced": _view(circle_schedule(league))}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
