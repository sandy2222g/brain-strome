"""FastAPI app. Stateless: the browser keeps the plant list and sends it with each request."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from plantparent.care import MAX_MULT, MIN_MULT, Plant, schedule, update_multiplier
from plantparent.model import IntervalModel

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "interval.joblib"))
DATA = ROOT / "data"


class PlantIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    species: str
    pot_cm: float = Field(ge=4, le=80)
    material: Literal["terracotta", "plastic", "ceramic"]
    last_watered: date
    multiplier: float = Field(default=1.0, ge=MIN_MULT, le=MAX_MULT)


class ScheduleIn(BaseModel):
    plants: list[PlantIn] = Field(min_length=1, max_length=60)
    today: date | None = None
    hemisphere: Literal["north", "south"] = "north"
    temp_c: float = Field(default=21.0, ge=5, le=35)
    humidity: float = Field(default=45.0, ge=10, le=95)
    pets: bool = False


class FeedbackIn(BaseModel):
    multiplier: float = Field(default=1.0, ge=MIN_MULT, le=MAX_MULT)
    soil: Literal["dry", "ok", "wet"]


def get_model() -> IntervalModel:
    if MODEL_PATH.exists():
        return IntervalModel.load(MODEL_PATH)
    m = IntervalModel()
    m.fit(pd.read_csv(DATA / "observations.csv"))
    try:
        m.save(MODEL_PATH)
    except OSError:
        pass
    return m


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.model = get_model()
    app.state.species = pd.read_csv(DATA / "species.csv")
    yield


app = FastAPI(title="Plant Parent", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return dict(app.state.model.metrics)


@app.get("/species")
def species() -> list[dict[str, Any]]:
    return list(app.state.species.to_dict("records"))


@app.get("/sample")
def sample() -> dict[str, Any]:
    t = date.today()
    mk = lambda n, s, pot, mat, ago: {  # noqa: E731
        "name": n,
        "species": s,
        "pot_cm": pot,
        "material": mat,
        "last_watered": (t - timedelta(days=ago)).isoformat(),
        "multiplier": 1.0,
    }
    return {
        "hemisphere": "north",
        "temp_c": 21,
        "humidity": 45,
        "pets": True,
        "plants": [
            mk("Monty", "Monstera", 24, "plastic", 9),
            mk("Sunny", "Snake plant", 15, "terracotta", 12),
            mk("Fern Gully", "Boston fern", 17, "plastic", 5),
            mk("Penny", "Chinese money plant", 12, "ceramic", 7),
            mk("Basil bush", "Basil (kitchen)", 14, "terracotta", 4),
            mk("Zed", "ZZ plant", 20, "plastic", 6),
            mk("Hoyt", "Hoya", 12, "terracotta", 8),
        ],
    }


@app.post("/schedule")
def make_schedule(body: ScheduleIn) -> dict[str, Any]:
    plants = [Plant(p.name, p.species, p.pot_cm, p.material, p.last_watered, p.multiplier) for p in body.plants]
    try:
        return schedule(
            plants,
            app.state.species,
            app.state.model,
            body.today or date.today(),
            body.hemisphere,
            body.temp_c,
            body.humidity,
            pets=body.pets,
        )
    except KeyError as exc:
        raise HTTPException(422, f"unknown species: {exc.args[0]}") from exc


@app.post("/feedback")
def feedback(body: FeedbackIn) -> dict[str, float]:
    return {"multiplier": update_multiplier(body.multiplier, body.soil)}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
