"""FastAPI app for the habit streak keeper."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from streakkeep.core import StreakError, heatmap, load, strict_summary, summary

ROOT = Path(__file__).resolve().parents[2]


class StreakIn(BaseModel):
    done: list[str] = Field(max_length=5000)
    today: str
    grace_days: int = Field(default=1, ge=0, le=7)


app = FastAPI(title="Habit Streak Keeper", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/streak")
def streak(body: StreakIn) -> dict[str, Any]:
    try:
        today = date.fromisoformat(body.today)
        return {
            "streak": summary(body.done, today, body.grace_days),
            "strict": strict_summary(body.done, today),
            "heatmap": heatmap(body.done, today),
        }
    except (StreakError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
