"""FastAPI app for the transit pass chooser."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from farepass.core import DATA, MAX_RIDERS, FareError, best_option, break_even_rides_per_week, build

ROOT = Path(__file__).resolve().parents[2]


class RiderIn(BaseModel):
    name: str = Field(max_length=40)
    weeks: list[list[int]] = Field(min_length=4, max_length=4)


class ChooseIn(BaseModel):
    fares: dict[str, float]
    riders: list[RiderIn] = Field(min_length=1, max_length=MAX_RIDERS)


app = FastAPI(title="Transit Pass Chooser", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/choose")
def choose(body: ChooseIn) -> dict[str, Any]:
    try:
        fares, riders = build(body.fares, [r.model_dump() for r in body.riders])
    except (FareError, KeyError) as err:
        raise HTTPException(422, str(err)) from err
    out = []
    for r in riders:
        best, costs = best_option(fares, r)
        out.append(
            {
                "name": r.name,
                "rides": sum(sum(w) for w in r.weeks),
                "best": best,
                "costs": costs,
                "saving_vs_single": round(costs["single"] - costs[best], 2),
            }
        )
    return {"riders": out, "week_pass_break_even_rides": round(break_even_rides_per_week(fares), 1)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
