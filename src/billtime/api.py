"""FastAPI app for the bill timing planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from billtime.core import BillError, balances, load, shortfalls, suggest_moves

ROOT = Path(__file__).resolve().parents[2]


class MonthIn(BaseModel):
    days: int = Field(ge=1, le=62)
    opening_balance: float
    income: list[dict[str, Any]]
    bills: list[dict[str, Any]]


app = FastAPI(title="Bill Timing Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/check")
def check(body: MonthIn) -> dict[str, Any]:
    month = body.model_dump()
    try:
        series = balances(month)
        fix = suggest_moves(month)
    except (BillError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err
    return {"balances": series, "shortfalls": shortfalls(series), "fix": fix}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
