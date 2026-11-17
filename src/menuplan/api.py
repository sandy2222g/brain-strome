"""FastAPI app for the weekly menu planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from menuplan.core import MenuError, list_order_plan, load, plan, violations

ROOT = Path(__file__).resolve().parents[2]


class PlanIn(BaseModel):
    dishes: list[dict[str, Any]]
    days: list[str] = Field(min_length=1, max_length=7)
    weeknight_max_min: int = Field(default=30, ge=5, le=240)


app = FastAPI(title="Weekly Menu Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def make_plan(body: PlanIn) -> dict[str, Any]:
    try:
        rows = plan(body.dishes, body.days, body.weeknight_max_min)
        naive = list_order_plan(body.dishes, body.days)
        bad = violations(naive, body.weeknight_max_min)
    except (MenuError, KeyError, TypeError) as err:
        raise HTTPException(422, str(err)) from err
    return {"plan": rows, "list_order_violations": bad}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
