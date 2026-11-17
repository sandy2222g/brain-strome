"""FastAPI app for the flat rent estimator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rentest.core import FEATURES, RentError, evaluate, trained

ROOT = Path(__file__).resolve().parents[2]
MODEL = trained()


class In(BaseModel):
    area_m2: float = Field(ge=10, le=300)
    bedrooms: int = Field(ge=0, le=8)
    distance_km: float = Field(ge=0, le=60)
    age_years: int = Field(ge=0, le=150)


app = FastAPI(title="Flat Rent Estimator", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return evaluate()


@app.post("/estimate")
def run(body: In) -> dict[str, Any]:
    try:
        rent = MODEL.predict([getattr(body, f) for f in FEATURES])
    except RentError as err:
        raise HTTPException(422, str(err)) from err
    return {"rent": round(rent), "per_unit": {k: round(v, 2) for k, v in MODEL.per_unit().items()}}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
