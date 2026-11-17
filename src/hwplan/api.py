"""FastAPI app for the homework order planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from hwplan.core import PlanError, in_order, load, moore_hodgson, shortest_first

ROOT = Path(__file__).resolve().parents[2]


class PlanIn(BaseModel):
    tasks: list[dict[str, Any]] = Field(max_length=500)


app = FastAPI(title="Homework Order Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    try:
        best = moore_hodgson(body.tasks)
        listed = in_order(body.tasks)
        short = shortest_first(body.tasks)
    except (PlanError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err
    return {"plan": best, "listed_on_time": listed["on_time_count"], "shortest_on_time": short["on_time_count"]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
