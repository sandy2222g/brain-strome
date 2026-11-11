"""FastAPI app for the shopping typo matcher."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from itemmatch.core import MatchError, best_match, build, exact_match, load

ROOT = Path(__file__).resolve().parents[2]


class MatchIn(BaseModel):
    catalogue: list[str]
    items: list[str]


app = FastAPI(title="Shopping Typo Matcher", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.post("/match")
def match(body: MatchIn) -> dict[str, Any]:
    try:
        cat, items = build(body.catalogue, body.items)
    except MatchError as err:
        raise HTTPException(422, str(err)) from err
    rows = []
    for raw, item in zip(body.items, items, strict=True):
        name, dist = best_match(item, cat)
        rows.append({"typed": raw, "match": name, "distance": dist, "exact": exact_match(item, cat)})
    return {
        "rows": rows,
        "fuzzy_found": sum(r["match"] is not None for r in rows),
        "exact_found": sum(r["exact"] is not None for r in rows),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
