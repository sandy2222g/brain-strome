"""FastAPI app for the savings goal planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from savegoal.core import (
    GoalError,
    balance_curve,
    load,
    months_to_goal,
    months_without_interest,
    required_monthly,
)

ROOT = Path(__file__).resolve().parents[2]


class GoalIn(BaseModel):
    goal: float
    start: float
    monthly: float
    annual_rate: float
    target_months: int


app = FastAPI(title="Savings Goal Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def plan(g: GoalIn) -> dict[str, Any]:
    try:
        months = months_to_goal(g.goal, g.start, g.monthly, g.annual_rate)
        need = required_monthly(g.goal, g.start, g.target_months, g.annual_rate)
    except GoalError as err:
        raise HTTPException(422, str(err)) from err
    horizon = min(months or g.target_months, 120)
    return {
        "months_with_interest": months,
        "months_without_interest": months_without_interest(g.goal, g.start, g.monthly),
        "required_monthly": round(need, 2),
        "required_monthly_no_interest": round(max(0.0, (g.goal - g.start) / g.target_months), 2),
        "curve": [round(x, 2) for x in balance_curve(g.start, g.monthly, g.annual_rate, horizon)],
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
