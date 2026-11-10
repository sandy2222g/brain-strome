"""FastAPI app: report a lost item, hand in a found item, see ranked candidates."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from lostfound.features import PLACE_XY
from lostfound.matcher import Matcher

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "matcher.joblib"))
DATA = ROOT / "data"
MAX_FOUND = 2000  # demo pool lives in memory only


class LostIn(BaseModel):
    description: str = Field(min_length=3, max_length=300)
    place: str = Field(default="main gate", max_length=40)
    date: date


class FoundIn(LostIn):
    pass


def get_matcher() -> Matcher:
    if MODEL_PATH.exists():
        return Matcher.load(MODEL_PATH)
    m = Matcher()
    m.fit(pd.read_csv(DATA / "found.csv"), pd.read_csv(DATA / "lost.csv"))
    try:
        m.save(MODEL_PATH)
    except OSError:
        pass
    return m


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.matcher = get_matcher()
    app.state.found = pd.read_csv(DATA / "found.csv")
    yield


app = FastAPI(title="Lost and Found Matcher", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return dict(app.state.matcher.metrics)


@app.get("/places")
def places() -> list[str]:
    return sorted(PLACE_XY)


@app.get("/found")
def found(limit: int = 20) -> dict[str, Any]:
    df: pd.DataFrame = app.state.found
    rows = df.sort_values("date", ascending=False).head(max(1, min(limit, 200)))
    return {"total": int(len(df)), "items": rows.to_dict("records")}


@app.post("/match")
def match(body: LostIn) -> dict[str, Any]:
    m: Matcher = app.state.matcher
    cands = m.match(body.model_dump(mode="json"), app.state.found, k=5)
    top = cands[0].score if cands else 0.0
    return {
        "confident": bool(cands) and m.is_confident(top),
        "threshold": round(m.threshold, 3),
        "candidates": [c.__dict__ for c in cands],
    }


@app.post("/found", status_code=201)
def hand_in(body: FoundIn) -> dict[str, str]:
    df: pd.DataFrame = app.state.found
    if len(df) >= MAX_FOUND:
        raise HTTPException(409, "the demo pool is full")
    new_id = f"F{len(df):04d}"
    row = {"id": new_id, "date": body.date.isoformat(), "place": body.place, "description": body.description}
    app.state.found = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return {"id": new_id}


@app.get("/sample-lost")
def sample_lost() -> list[dict[str, str]]:
    lost = pd.read_csv(DATA / "lost.csv")
    pick = pd.concat([lost[lost["match_id"].notna()].head(3), lost[lost["match_id"].isna()].head(1)])
    return pick[["description", "place", "date"]].to_dict("records")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
