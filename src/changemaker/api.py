"""FastAPI app for the coin change maker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from changemaker.core import ChangeError, build, fewest_coins, greedy, load

ROOT = Path(__file__).resolve().parents[2]


class ChangeIn(BaseModel):
    till: dict[str, int]
    amounts: list[int] = Field(min_length=1, max_length=20)


app = FastAPI(title="Coin Change Maker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


def _fmt(plan: dict[int, int] | None) -> dict[str, Any]:
    return {
        "possible": plan is not None,
        "coins": sum(plan.values()) if plan else 0,
        "detail": {str(k): v for k, v in (plan or {}).items()},
    }


@app.post("/change")
def change(body: ChangeIn) -> dict[str, Any]:
    try:
        till = build(body.till, 0)
        for a in body.amounts:
            build(body.till, a)
        rows = [
            {"amount": a, "fewest": _fmt(fewest_coins(till, a)), "greedy": _fmt(greedy(till, a))} for a in body.amounts
        ]
    except (ChangeError, ValueError) as err:
        raise HTTPException(422, str(err)) from err
    return {"rows": rows}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
