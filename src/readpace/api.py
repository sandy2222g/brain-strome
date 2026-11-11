"""FastAPI app for the reading pace planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from readpace.core import PlanError, build, load, naive_pages_per_day, naive_total, plan, reading_days

ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="Reading Pace Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def make_plan(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        b = build(raw)
        days = plan(b)
    except PlanError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "title": b.title,
        "pages_left": b.pages - b.pages_read,
        "reading_days": len(reading_days(b)),
        "schedule": [{"date": d.isoformat(), "weekday": d.weekday(), "pages": p} for d, p in days],
        "naive_per_day": naive_pages_per_day(b),
        "naive_total": naive_total(b),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
