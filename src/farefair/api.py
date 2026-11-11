"""FastAPI app for the taxi fare splitter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from farefair.core import (
    DATA,
    MAX_RIDERS,
    FareError,
    Rider,
    alone_cost,
    build,
    distance_split,
    equal_split,
    shapley,
    total_fare,
)

ROOT = Path(__file__).resolve().parents[2]


class RiderIn(BaseModel):
    name: str = Field(max_length=30)
    stop: list[float] = Field(min_length=2, max_length=2)


class FareIn(BaseModel):
    rate_per_km: float = Field(gt=0, le=100)
    start: list[float] = Field(min_length=2, max_length=2)
    riders: list[RiderIn] = Field(min_length=1, max_length=MAX_RIDERS)


app = FastAPI(title="Taxi Fare Splitter", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(DATA.read_text())


@app.post("/split")
def split(body: FareIn) -> dict[str, Any]:
    try:
        ride = build(
            [Rider(r.name, (r.stop[0], r.stop[1])) for r in body.riders],
            (body.start[0], body.start[1]),
            body.rate_per_km,
        )
    except FareError as err:
        raise HTTPException(422, str(err)) from err
    alone = [alone_cost(ride, i) for i in range(len(ride.riders))]
    methods = {"equal": equal_split(ride), "distance": distance_split(ride), "shapley": shapley(ride)}
    return {
        "total": round(total_fare(ride), 2),
        "riders": [
            {
                "name": r.name,
                "alone": round(alone[i], 2),
                **{k: round(v[i], 2) for k, v in methods.items()},
            }
            for i, r in enumerate(ride.riders)
        ],
        "over_alone": {k: sum(v[i] > alone[i] + 0.005 for i in range(len(alone))) for k, v in methods.items()},
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
