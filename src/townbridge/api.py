from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import TownError, best_new_roads, closure, load_town, tarjan

app = FastAPI(title="Town Bridge Finder")
TOWN = load_town()
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/town")
def town() -> dict[str, object]:
    bridges, cuts = tarjan(TOWN.adjacency())
    return {"places": TOWN.places, "roads": TOWN.roads, "bridges": bridges, "junctions": cuts,
            "suggestions": best_new_roads(TOWN)}


@app.get("/close")
def close(a: str, b: str) -> dict[str, object]:
    try:
        parts = closure(TOWN, (a, b))
    except TownError as e:
        raise HTTPException(404, str(e)) from e
    return {"closed": [a, b], "pieces": parts, "split": len(parts) > 1}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
