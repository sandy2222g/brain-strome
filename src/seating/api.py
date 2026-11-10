"""FastAPI app: solve a seating plan, score a manual edit, serve the UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from seating.model import Guest, Problem, Scorer, SeatingError, Solution, describe, solve

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "sample_party.json"


class GuestIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    group: str = Field(default="", max_length=40)


class PartyIn(BaseModel):
    guests: list[GuestIn] = Field(min_length=1, max_length=200)
    likes: list[tuple[str, str]] = Field(default_factory=list, max_length=500)
    dislikes: list[tuple[str, str]] = Field(default_factory=list, max_length=500)
    together: list[list[str]] = Field(default_factory=list, max_length=100)
    apart: list[tuple[str, str]] = Field(default_factory=list, max_length=500)
    table_size: int = Field(default=8, ge=1, le=20)
    seed: int = Field(default=0, ge=0, le=10_000)


class ScoreIn(PartyIn):
    tables: list[list[str]]


app = FastAPI(title="Wedding Seating Planner", version="1.0.0")


def _problem(p: PartyIn) -> Problem:
    return Problem(
        guests=[Guest(g.name, g.group) for g in p.guests],
        likes=list(p.likes),
        dislikes=list(p.dislikes),
        together=p.together,
        apart=list(p.apart),
        table_size=p.table_size,
    )


def _out(s: Solution) -> dict[str, Any]:
    return s.__dict__


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SAMPLE.read_text())
    return data


@app.post("/solve")
def solve_party(body: PartyIn) -> dict[str, Any]:
    try:
        return _out(solve(_problem(body), seed=body.seed))
    except SeatingError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/score")
def score_arrangement(body: ScoreIn) -> dict[str, Any]:
    problem = _problem(body)
    try:
        return _out(describe(problem, body.tables, Scorer(problem), body.seed))
    except SeatingError as exc:
        raise HTTPException(422, str(exc)) from exc


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
