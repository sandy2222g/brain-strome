"""FastAPI app for the debt payoff strategist."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from debtplan.core import DebtError, compare, load

ROOT = Path(__file__).resolve().parents[2]


class DebtIn(BaseModel):
    budget: float = Field(gt=0)
    debts: list[dict[str, Any]] = Field(max_length=30)


app = FastAPI(title="Debt Payoff Strategist", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/compare")
def run(body: DebtIn) -> dict[str, Any]:
    try:
        return compare(body.debts, body.budget)
    except (DebtError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
