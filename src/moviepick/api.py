"""FastAPI app for the group movie recommender."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from moviepick.core import (
    PickError,
    baselines,
    evaluate_groups,
    fit,
    group_pick,
    holdout,
    load,
    rmse,
    to_matrix,
)

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def state() -> dict[str, Any]:
    d = load()
    n_u, n_f = len(d["users"]), len(d["films"])
    r, mask = to_matrix(d["ratings"], n_u, n_f)
    model = fit(r, mask)
    return {"data": d, "r": r, "mask": mask, "pred": model.predict(), "true": np.array(d["true_ratings"])}


class PickIn(BaseModel):
    members: list[int] = Field(min_length=1, max_length=12)
    strategy: str = Field(default="least_misery")


app = FastAPI(title="Movie Night Recommender", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    d = state()["data"]
    return {"users": d["users"], "films": d["films"]}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    s = state()
    train, test = holdout(s["mask"])
    model = fit(np.where(train, s["r"], 0.0), train)
    glob, film = baselines(s["r"], train)
    return {
        "rmse_model": round(rmse(model.predict(), s["r"], test), 3),
        "rmse_film_mean": round(rmse(film, s["r"], test), 3),
        "rmse_global_mean": round(rmse(glob, s["r"], test), 3),
        "test_ratings": int(test.sum()),
        "group_eval": evaluate_groups(s["pred"], s["true"], s["mask"]),
    }


@app.post("/pick")
def pick(body: PickIn) -> dict[str, Any]:
    s = state()
    n_u = len(s["data"]["users"])
    if any(m < 0 or m >= n_u for m in body.members) or len(set(body.members)) != len(body.members):
        raise HTTPException(422, "members must be distinct valid viewer indexes")
    try:
        picks = group_pick(s["pred"], body.members, s["mask"], body.strategy)
    except PickError as err:
        raise HTTPException(422, str(err)) from err
    films = s["data"]["films"]
    return {"picks": [{**p, "title": films[p["film"]]["title"], "genre": films[p["film"]]["genre"]} for p in picks]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
