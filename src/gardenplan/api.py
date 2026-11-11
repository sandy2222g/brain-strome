"""FastAPI app for the planting calendar."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from gardenplan.core import PlanError, build, load_crops

ROOT = Path(__file__).resolve().parents[2]


class PlanIn(BaseModel):
    crops: list[str] = Field(min_length=1, max_length=20)
    last_frost: date
    first_frost: date
    beds: int = Field(default=2, ge=1, le=12)
    hot_from: date | None = None


app = FastAPI(title="Garden Planting Calendar", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/crops")
def crops() -> list[str]:
    return sorted(load_crops())


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    try:
        r = build(body.crops, body.last_frost, body.first_frost, body.beds, body.hot_from)
    except PlanError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "plan": {
            k: [{"sow": s.sow.isoformat(), "harvest": s.harvest.isoformat()} for s in v] for k, v in r["plan"].items()
        },  # type: ignore[attr-defined]
        "layout": r["layout"],
        "conflicts": r["conflicts"],
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
