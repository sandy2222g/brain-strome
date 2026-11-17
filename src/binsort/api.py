"""FastAPI app for the waste bin sorter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from binsort.core import SortError, evaluate, trained

ROOT = Path(__file__).resolve().parents[2]
MODEL = trained()


class In(BaseModel):
    item: str = Field(min_length=1, max_length=200)


app = FastAPI(title="Waste Bin Sorter", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return evaluate()


@app.post("/classify")
def run(body: In) -> dict[str, Any]:
    try:
        p = MODEL.proba(body.item)
    except SortError as err:
        raise HTTPException(422, str(err)) from err
    best = max(p, key=lambda c: (p[c], c))
    known = [w for w in set(body.item.lower().split()) if w in MODEL.vocab]
    return {"bin": best, "probabilities": {c: round(v, 3) for c, v in p.items()}, "known_words": len(known)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
