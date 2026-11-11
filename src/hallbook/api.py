"""FastAPI app for the hall booking optimizer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from hallbook.core import (
    DATA,
    MAX_REQUESTS,
    BookingError,
    Request,
    best_bookings,
    build,
    earliest_finish,
    first_come_first_served,
    hours,
    revenue,
)

ROOT = Path(__file__).resolve().parents[2]


class RequestIn(BaseModel):
    name: str = Field(max_length=60)
    start: str
    end: str
    fee: float = Field(ge=0, le=1_000_000)


class BookIn(BaseModel):
    requests: list[RequestIn] = Field(min_length=1, max_length=MAX_REQUESTS)


app = FastAPI(title="Hall Booking Optimizer", version="1.0.0")


def _view(chosen: list[Request]) -> dict[str, Any]:
    return {
        "revenue": revenue(chosen),
        "bookings": len(chosen),
        "hours": round(hours(chosen), 2),
        "accepted": [r.name for r in chosen],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/book")
def book(body: BookIn) -> dict[str, Any]:
    try:
        requests = build([r.model_dump() for r in body.requests])
    except (BookingError, KeyError) as err:
        raise HTTPException(422, str(err)) from err
    return {
        "first_come": _view(first_come_first_served(requests)),
        "earliest_finish": _view(earliest_finish(requests)),
        "best": _view(best_bookings(requests)),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
