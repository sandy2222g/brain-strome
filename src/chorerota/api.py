"""FastAPI app for the chore rota."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chorerota.core import (
    DATA,
    MAX_PEOPLE,
    Chore,
    Person,
    RotaError,
    effort_spread,
    efforts,
    fair_rota,
    round_robin,
    total_dislike,
    worst_streak,
)

ROOT = Path(__file__).resolve().parents[2]


class PersonIn(BaseModel):
    name: str = Field(max_length=30)
    dislike: dict[str, int]


class ChoreIn(BaseModel):
    name: str = Field(max_length=30)
    effort: int = Field(gt=0, le=20)


class RotaIn(BaseModel):
    people: list[PersonIn] = Field(min_length=1, max_length=MAX_PEOPLE)
    chores: list[ChoreIn] = Field(min_length=1, max_length=MAX_PEOPLE)
    weeks: int = Field(default=8, ge=1, le=52)
    balance: float = Field(default=6.0, ge=0, le=50)


app = FastAPI(title="Chore Rota", version="1.0.0")


def _summary(rota: list[list[int]], people: list[Person], chores: list[Chore]) -> dict[str, Any]:
    return {
        "weeks": [[people[pi].name for pi in week] for week in rota],
        "dislike": total_dislike(rota, people, chores),
        "effort_by_person": dict(zip((p.name for p in people), efforts(rota, chores, len(people)), strict=True)),
        "effort_spread": effort_spread(rota, chores, len(people)),
        "worst_streak": worst_streak(rota),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/rota")
def rota(body: RotaIn) -> dict[str, Any]:
    people = [Person(p.name, p.dislike) for p in body.people]
    chores = [Chore(c.name, c.effort) for c in body.chores]
    try:
        fair = fair_rota(people, chores, body.weeks, balance=body.balance)
        rr = round_robin(people, chores, body.weeks)
    except RotaError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "chores": [c.name for c in chores],
        "fair": _summary(fair, people, chores),
        "round_robin": _summary(rr, people, chores),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
