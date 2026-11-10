"""FastAPI application: urgency ranking, recipe suggestions, weekly plan and the web UI."""
from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pantry.planner import plan_week
from pantry.recipes import RecipeRanker, ScoredRecipe, load_recipes
from pantry.train import train
from pantry.urgency import PantryItem, RawItem, enrich, prioritize
from pantry.waste_model import WasteModel

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "waste.joblib"))
RECIPES_PATH = ROOT / "data" / "recipes.csv"

SAMPLE_OFFSETS: list[tuple[str, int, float, str | None]] = [
    ("milk", 1, 1, None), ("spinach", 2, 1, None), ("chicken breast", 2, 1, None), ("tomato", 3, 4, None),
    ("yogurt", 4, 2, None), ("bread", 0, 1, None), ("mushroom", 1, 1, None), ("egg", 9, 6, None),
    ("rice", 200, 1, "pantry"), ("pasta", 300, 1, "pantry"), ("canned tomato", 400, 2, None),
    ("onion", 14, 4, None), ("cheddar", 20, 1, None), ("bell pepper", 4, 2, None), ("carrot", 10, 5, None),
    ("lettuce", -1, 1, None),
]  # fmt: skip


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    expiry: date | None = None
    quantity: float = Field(default=1.0, gt=0, le=100)
    storage: Literal["fridge", "pantry", "freezer"] | None = None
    purchased: date | None = None


class PantryIn(BaseModel):
    items: list[ItemIn] = Field(min_length=1, max_length=200)
    household_size: int = Field(default=2, ge=1, le=10)
    today: date | None = None


class RecipesIn(PantryIn):
    limit: int = Field(default=5, ge=1, le=20)


class PlanIn(PantryIn):
    days: int = Field(default=7, ge=1, le=14)


def get_model() -> WasteModel:
    if MODEL_PATH.exists():
        return WasteModel.load(MODEL_PATH)
    try:
        return train(MODEL_PATH)
    except OSError:  # read-only filesystem
        return train(Path(tempfile.gettempdir()) / "waste.joblib")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    app.state.model = get_model()
    app.state.ranker = RecipeRanker(load_recipes(RECIPES_PATH))
    yield


app = FastAPI(title="Pantry Saver", version="1.0.0", lifespan=lifespan)


def _raws(p: PantryIn) -> list[RawItem]:
    return [RawItem(i.name, i.expiry, i.quantity, i.storage, i.purchased) for i in p.items]


def _item(i: PantryItem) -> dict[str, Any]:
    return {
        "idx": i.idx, "name": i.name, "canonical": i.canonical, "category": i.category, "storage": i.storage,
        "kg": i.kg, "expiry": i.expiry.isoformat(), "days_left": i.days_left, "p_waste": i.p_waste,
        "urgency": i.urgency, "status": i.status,
    }  # fmt: skip


def _recipe(s: ScoredRecipe) -> dict[str, Any]:
    r = s.recipe
    return {
        "id": r.id, "name": r.name, "minutes": r.minutes, "servings": r.servings, "steps": r.steps,
        "score": s.score, "match": s.cosine, "uses": [{"name": u.name, "days_left": u.days_left} for u in s.used],
        "missing": s.missing, "waste_kg": s.waste_kg, "waste_value": s.waste_value,
    }  # fmt: skip


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return {"waste_model": app.state.model.metrics, "recipes": len(app.state.ranker.recipes)}


@app.get("/sample")
def sample() -> dict[str, Any]:
    today = date.today()
    items = [
        {"name": n, "expiry": (today + timedelta(days=d)).isoformat(), "quantity": q, "storage": s}
        for n, d, q, s in SAMPLE_OFFSETS
    ]
    return {"items": items, "household_size": 2, "today": today.isoformat()}


@app.post("/prioritize")
def prioritize_items(req: PantryIn) -> dict[str, Any]:
    today = req.today or date.today()
    items = prioritize(enrich(_raws(req), today, req.household_size, app.state.model))
    return {"today": today.isoformat(), "items": [_item(i) for i in items]}


@app.post("/recipes")
def recipes(req: RecipesIn) -> dict[str, Any]:
    today = req.today or date.today()
    items = enrich(_raws(req), today, req.household_size, app.state.model)
    ranked = app.state.ranker.rank(items, limit=req.limit)
    return {
        "recipes": [_recipe(s) for s in ranked],
        "best_waste_kg": ranked[0].waste_kg if ranked else 0.0,
        "best_waste_value": ranked[0].waste_value if ranked else 0.0,
    }


@app.post("/plan")
def plan(req: PlanIn) -> dict[str, Any]:
    today = req.today or date.today()
    p = plan_week(_raws(req), app.state.ranker, app.state.model, today, req.household_size, req.days)
    return {
        "days": [{"date": d.day.isoformat(), "recipe": _recipe(d.pick) if d.pick else None} for d in p.days],
        "waste_kg": p.waste_kg,
        "waste_value": p.waste_value,
        "left_over_at_risk": [_item(i) for i in p.left_over_at_risk],
    }


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
