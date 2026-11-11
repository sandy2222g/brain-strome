"""FastAPI app for the grocery aisle route planner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from aislewalk.core import RouteError, best_route, list_order_route, load, route_length, steps

ROOT = Path(__file__).resolve().parents[2]
STORE = load()


class RouteIn(BaseModel):
    items: list[str] = Field(min_length=1, max_length=40)


app = FastAPI(title="Grocery Aisle Route", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/store")
def store() -> dict[str, Any]:
    return {
        "aisles": STORE.aisles,
        "depth": STORE.depth,
        "aisle_gap": STORE.aisle_gap,
        "aisle_names": STORE.names,
        "items": {k: list(v) for k, v in STORE.items.items()},
    }


@app.post("/route")
def route(body: RouteIn) -> dict[str, Any]:
    try:
        best = best_route(STORE, body.items)
        naive = list_order_route(STORE, body.items)
    except RouteError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "order": best,
        "steps": steps(STORE, best),
        "length": route_length(STORE, best),
        "list_order_length": route_length(STORE, naive),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
