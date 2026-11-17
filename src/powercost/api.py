"""FastAPI app for the appliance power cost calculator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from powercost.core import PowerError, load, report

ROOT = Path(__file__).resolve().parents[2]


class HomeIn(BaseModel):
    days: int = Field(default=30, ge=1, le=366)
    tariff: dict[str, float]
    appliances: list[dict[str, Any]] = Field(max_length=200)


app = FastAPI(title="Appliance Power Cost", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/report")
def make_report(body: HomeIn) -> dict[str, Any]:
    try:
        return report(body.model_dump())
    except (PowerError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
