"""FastAPI app: match a cohort into study pairs and explain each pair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from buddies.model import BuddyError, Student, match, pair_score

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "students.json"


class StudentIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    skills: dict[str, int] = Field(default_factory=dict)
    slots: list[str] = Field(default_factory=list, max_length=21)
    style: str = Field(default="quiet", pattern="^(quiet|chatty)$")
    goal: str = Field(default="exam", pattern="^(exam|ongoing)$")

    def to_student(self) -> Student:
        return Student(self.name, self.skills, tuple(self.slots), self.style, self.goal)


class CohortIn(BaseModel):
    students: list[StudentIn] = Field(min_length=2, max_length=200)
    seed: int = Field(default=0, ge=0, le=100000)


app = FastAPI(title="Study Buddy Matcher", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SAMPLE.read_text())
    return data


@app.post("/match")
def run_match(body: CohortIn) -> dict[str, Any]:
    students = [s.to_student() for s in body.students]
    try:
        r = match(students, seed=body.seed)
    except BuddyError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        "pairs": [p.__dict__ for p in r.pairs],
        "total_score": r.total_score,
        "random_baseline": r.random_baseline,
        "blocking_pairs": r.blocking_pairs,
        "students": len(students),
    }


@app.post("/compatibility")
def compatibility(a: StudentIn, b: StudentIn) -> dict[str, float]:
    return {"score": pair_score(a.to_student(), b.to_student())}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
