"""FastAPI app for the timetable builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from timetable.core import (
    DATA,
    MAX_COURSES,
    Course,
    Section,
    TimetableError,
    best_timetable,
    build_courses,
    campus_days,
    credits_of,
    idle_minutes,
    register_in_order,
)

ROOT = Path(__file__).resolve().parents[2]


class SectionIn(BaseModel):
    code: str = Field(max_length=20)
    meetings: list[list[str]] = Field(min_length=1, max_length=10)


class CourseIn(BaseModel):
    name: str = Field(max_length=50)
    credits: int = Field(gt=0, le=30)
    required: bool = False
    sections: list[SectionIn] = Field(min_length=1, max_length=8)


class BuildIn(BaseModel):
    max_credits: int = Field(gt=0, le=60)
    courses: list[CourseIn] = Field(min_length=1, max_length=MAX_COURSES)


app = FastAPI(title="Timetable Builder", version="1.0.0")


def _view(courses: list[Course], taken: dict[str, Section]) -> dict[str, Any]:
    chosen = list(taken.values())
    return {
        "credits": credits_of(courses, taken),
        "days": campus_days(chosen),
        "idle_minutes": idle_minutes(chosen),
        "missing_required": [c.name for c in courses if c.required and c.name not in taken],
        "classes": [
            {"course": name, "code": s.code, "meetings": [[d, a, b] for d, a, b in s.meetings]}
            for name, s in taken.items()
        ],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/build")
def build(body: BuildIn) -> dict[str, Any]:
    try:
        courses = build_courses([c.model_dump() for c in body.courses])
        return {
            "in_order": _view(courses, register_in_order(body.max_credits, courses)),
            "best": _view(courses, best_timetable(body.max_credits, courses)),
        }
    except (TimetableError, ValueError, KeyError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
