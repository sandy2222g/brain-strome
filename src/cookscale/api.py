"""FastAPI app: scale recipes and price the shopping list."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cookscale.core import CookError, combine, load, scale, shared_vs_separate, shopping_list, total, waste_value

ROOT = Path(__file__).resolve().parents[2]


class CookIn(BaseModel):
    recipes: list[str] = Field(min_length=1, max_length=10)
    people: int = Field(ge=1, le=60)
    on_hand: dict[str, float] = Field(default_factory=dict)


app = FastAPI(title="Recipe Scaler", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recipes")
def recipes() -> list[dict[str, Any]]:
    _, r = load()
    return [{"name": x.name, "serves": x.serves, "items": x.items} for x in r.values()]


@app.post("/shop")
def shop(body: CookIn) -> dict[str, Any]:
    packs, rec = load()
    missing = [n for n in body.recipes if n not in rec]
    if missing:
        raise HTTPException(422, f"unknown recipes: {', '.join(missing)}")
    chosen = [rec[n] for n in body.recipes]
    try:
        lines = shopping_list(combine([scale(r, body.people) for r in chosen]), packs, body.on_hand)
        comb, sep = shared_vs_separate(chosen, body.people, packs)
    except CookError as err:
        raise HTTPException(422, str(err)) from err
    return {
        "lines": [x.__dict__ for x in lines],
        "total": total(lines),
        "waste_value": waste_value(lines, packs),
        "combined_cost": comb,
        "separate_cost": sep,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
