"""FastAPI app: plan generation, score estimate, forgetting-curve preview, UI."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from runway.memory import retention
from runway.planner import Topic, build_plan
from runway.predictor import ScoreModel, load_dataset

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "score.joblib"))
DATA_PATH = ROOT / "data" / "study_sessions.csv"


class TopicIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    weight: float = Field(gt=0, le=100, default=1.0, description="share of exam marks")
    difficulty: float = Field(ge=0, le=1, default=0.5)
    confidence: float = Field(ge=0, le=1, default=0.2)


class PlanIn(BaseModel):
    topics: list[TopicIn] = Field(min_length=1, max_length=30)
    exam_date: date
    start: date | None = None
    hours_per_day: float = Field(gt=0, le=16, default=3.0)
    rest_weekdays: list[int] = Field(default_factory=list, max_length=6)
    sleep_hours: float = Field(ge=3, le=12, default=7.0)


def get_score_model() -> ScoreModel:
    if MODEL_PATH.exists():
        return ScoreModel.load(MODEL_PATH)
    m = ScoreModel()
    m.fit(load_dataset(DATA_PATH))
    try:
        m.save(MODEL_PATH)
    except OSError:
        pass
    return m


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    app.state.score = get_score_model()
    yield


app = FastAPI(title="Exam Runway", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return dict(app.state.score.metrics)


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    start = body.start or date.today()
    if any(not 0 <= d <= 6 for d in body.rest_weekdays):
        raise HTTPException(422, "rest_weekdays must be 0 (Mon) to 6 (Sun)")
    topics = [Topic(t.name, t.weight, t.difficulty, t.confidence) for t in body.topics]
    try:
        p = build_plan(topics, body.exam_date, start, body.hours_per_day, tuple(body.rest_weekdays))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    study_days = [d for d in p.days if d.sessions]
    sessions = sum(len(d.sessions) for d in study_days)
    total_w = sum(t.weight for t in topics)
    avg_diff = sum(t.difficulty * t.weight for t in topics) / total_w
    avg_conf = sum(t.confidence * t.weight for t in topics) / total_w
    per_topic_sessions = sessions / len(topics)
    spacing = (len(p.days) / per_topic_sessions) if per_topic_sessions else 0.0
    score = app.state.score.predict(
        total_hours=p.total_hours, n_sessions=max(sessions, 2), spacing_days=min(spacing, 7.0),
        difficulty=avg_diff, prior_confidence=avg_conf, sleep_hours=body.sleep_hours,
    )
    return {
        "start": start.isoformat(),
        "exam_date": body.exam_date.isoformat(),
        "total_hours": p.total_hours,
        "study_days": len(study_days),
        "exam_readiness": p.exam_readiness,
        "predicted_score": round(score, 1),
        "readiness": p.readiness,
        "half_life_days": p.half_life_days,
        "avg_half_life_days": round(sum(p.half_life_days.values()) / len(p.half_life_days), 1),
        "warnings": p.warnings,
        "days": [
            {
                "date": d.date.isoformat(),
                "hours": d.hours,
                "sessions": [
                    {"topic": s.topic, "hours": s.hours, "retention_before": s.retention_before} for s in d.sessions
                ],
            }
            for d in p.days
        ],
    }


@app.get("/curve")
def curve(stability: float = 3.0, days: int = 30) -> dict[str, Any]:
    if stability <= 0 or not 1 <= days <= 365:
        raise HTTPException(422, "stability must be > 0 and days within 1..365")
    return {"points": [{"day": d, "retention": round(retention(d, stability), 4)} for d in range(days + 1)]}


@app.get("/sample")
def sample() -> dict[str, Any]:
    today = date.today()
    return {
        "exam_date": (today + timedelta(days=21)).isoformat(),
        "hours_per_day": 3.0,
        "rest_weekdays": [6],
        "sleep_hours": 7.0,
        "topics": [
            {"name": "Organic chemistry", "weight": 3, "difficulty": 0.8, "confidence": 0.15},
            {"name": "Thermodynamics", "weight": 2, "difficulty": 0.6, "confidence": 0.3},
            {"name": "Linear algebra", "weight": 2, "difficulty": 0.5, "confidence": 0.5},
            {"name": "Lab report writing", "weight": 1, "difficulty": 0.2, "confidence": 0.6},
        ],
    }


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
