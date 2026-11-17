"""FastAPI app for the checkout line chooser."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from linepick.core import LineError, build, fewest_people, load, rank

ROOT = Path(__file__).resolve().parents[2]


class PickIn(BaseModel):
    lanes: list[dict[str, Any]]
    items: int = Field(ge=1, le=500)


app = FastAPI(title="Checkout Line Chooser", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/pick")
def pick(body: PickIn) -> dict[str, Any]:
    try:
        lanes = build(body.lanes)
        rows = rank(lanes, body.items)
        naive = fewest_people(lanes, body.items)
    except (LineError, KeyError, ValueError, TypeError) as err:
        raise HTTPException(422, str(err)) from err
    secs = {r["name"]: r["seconds"] for r in rows}
    best = rows[0]
    return {
        "rows": rows,
        "best": best["name"],
        "fewest_people": naive,
        "extra_seconds_if_fewest_people": round(secs[naive] - best["seconds"], 2),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
