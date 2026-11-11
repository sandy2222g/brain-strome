"""FastAPI app for the gift budget splitter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from giftbudget.core import Gift, GiftError, best_plan, build, equal_share_plan, load

ROOT = Path(__file__).resolve().parents[2]


class PlanIn(BaseModel):
    budget: int
    people: dict[str, list[dict[str, Any]]]


app = FastAPI(title="Gift Budget Splitter", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


def _fmt(plan: tuple[int, int, dict[str, Gift | None]]) -> dict[str, Any]:
    joy, spent, chosen = plan
    return {
        "joy": joy,
        "spent": spent,
        "gifts": {
            n: (None if g is None else {"name": g.name, "price": g.price, "joy": g.joy}) for n, g in chosen.items()
        },
    }


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    try:
        people = build(body.people, body.budget)
    except (GiftError, KeyError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    return {"optimal": _fmt(best_plan(people, body.budget)), "equal_share": _fmt(equal_share_plan(people, body.budget))}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
