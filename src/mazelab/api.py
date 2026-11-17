"""FastAPI app for the maze lab."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import GENERATORS, MazeError, compare, dead_ends, generate, solve

app = FastAPI(title="Maze Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/maze")
def maze(
    width: int = Query(20, ge=2, le=60), height: int = Query(14, ge=2, le=60), algorithm: str = "backtracker",
    seed: int = 0,
) -> dict[str, object]:
    try:
        m = generate(width, height, algorithm, seed)
        sols = {k: solve(m, k) for k in ("bfs", "dfs", "astar")}
    except MazeError as e:
        raise HTTPException(422, str(e)) from e
    return {
        "width": width, "height": height, "passages": sorted([list(a), list(b)] for a, b in m.passages),
        "dead_ends": dead_ends(m),
        "solutions": {k: {"path": [list(c) for c in s.path], "expanded": s.expanded} for k, s in sols.items()},
    }


@lru_cache(maxsize=1)
def _compare() -> list[dict[str, object]]:
    return compare(25, 25, 60)


@app.get("/compare")
def compare_all() -> dict[str, object]:
    return {"rows": _compare(), "algorithms": sorted(GENERATORS)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
