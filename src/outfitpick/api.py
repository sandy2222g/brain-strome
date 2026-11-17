"""FastAPI app."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Weather Outfit Picker")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Weather(BaseModel):
    temp_c: float
    wind_kph: float = 0
    rain_mm: float = 0


@lru_cache(maxsize=1)
def model() -> core.Model:
    return core.train(core.split(core.load())[0])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/evaluation")
def evaluation() -> dict[str, object]:
    return core.evaluate()


@app.post("/recommend")
def recommend(w: Weather) -> dict[str, object]:
    try:
        return core.recommend(model(), w.temp_c, w.wind_kph, w.rain_mm)
    except core.OutfitError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
