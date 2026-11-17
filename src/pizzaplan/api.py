"""FastAPI app for the pizza order planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pizzaplan.core import PizzaError, compare, load

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    slices_each: int = Field(ge=1, le=10)
    meat_pct: int = Field(default=0, ge=0, le=100)
    people: dict[str, int]
    menu: list[dict[str, Any]] = Field(max_length=8)


app = FastAPI(title="Pizza Order Planner", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/plan")
def run(body: In) -> dict[str, Any]:
    try:
        return compare(body.people, body.menu, body.slices_each, body.meat_pct)
    except (PizzaError, KeyError, TypeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
