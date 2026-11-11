"""FastAPI app: best meeting slots across time zones and a fair weekly rotation."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from meetfair.core import MeetingError, Person, Slot, best_slots, rotation, slot_pain, validate

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "sample_team.json"


class PersonIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    tz: str = Field(min_length=1, max_length=64)
    work_start: float = Field(default=9.0, ge=0, le=23)
    work_end: float = Field(default=17.0, gt=0, le=24)

    def to_person(self) -> Person:
        return Person(self.name, self.tz, self.work_start, self.work_end)


class MeetingIn(BaseModel):
    people: list[PersonIn] = Field(min_length=2, max_length=40)
    start_date: date
    duration_min: int = Field(default=60, ge=15, le=180)
    weeks: int = Field(default=8, ge=2, le=52)
    fairness: float = Field(default=1.0, ge=0, le=5, description="weight on the worst individual pain")


app = FastAPI(title="Fair Meeting Time", version="1.0.0")


def _slot(s: Slot) -> dict[str, Any]:
    return {
        "start_utc": s.start_utc.strftime("%Y-%m-%d %H:%M"),
        "total_pain": round(s.total_pain, 1),
        "worst_pain": round(s.worst_pain, 1),
        "sleepers": s.sleepers,
        "people": [p.__dict__ for p in s.people],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SAMPLE.read_text())
    return data


@app.post("/best")
def best(body: MeetingIn) -> dict[str, Any]:
    people = [p.to_person() for p in body.people]
    try:
        slots = best_slots(people, body.start_date, body.duration_min, 5, body.fairness)
    except MeetingError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "slots": [_slot(s) for s in slots],
        "warning": "Every option lands in someone's sleep." if slots[0].sleepers else None,
    }


@app.post("/bands")
def bands(body: MeetingIn) -> dict[str, Any]:
    """Pain of starting the meeting at each 30-minute step of the UTC day, per person (for the timeline view)."""
    people = [p.to_person() for p in body.people]
    try:
        validate(people, body.duration_min)
    except MeetingError as exc:
        raise HTTPException(422, str(exc)) from exc
    base = datetime(body.start_date.year, body.start_date.month, body.start_date.day, tzinfo=UTC)
    return {
        p.name: [round(slot_pain(p, base + timedelta(minutes=m), body.duration_min), 1) for m in range(0, 1440, 30)]
        for p in people
    }


@app.post("/rotation")
def rotate(body: MeetingIn) -> dict[str, Any]:
    people = [p.to_person() for p in body.people]
    try:
        r = rotation(people, body.start_date, body.weeks, body.duration_min, body.fairness)
    except MeetingError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "weeks": [_slot(s) for s in r.weeks],
        "cumulative": r.cumulative,
        "fixed_cumulative": r.fixed_cumulative,
        "spread": r.spread,
        "fixed_spread": r.fixed_spread,
        "max_pain": r.max_pain_rotation,
        "fixed_max_pain": r.max_pain_fixed,
    }


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
