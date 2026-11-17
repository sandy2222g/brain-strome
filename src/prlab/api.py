"""FastAPI app for the PageRank lab."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core import TOWN, RankError, damping_sweep, indegree_ranking, ranking

app = FastAPI(title="PageRank Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"


class Graph(BaseModel):
    links: dict[str, list[str]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/town")
def town(damping: float = Query(0.85, ge=0, lt=1)) -> dict[str, object]:
    return {
        "links": TOWN,
        "pagerank": [{"page": p, "score": round(s, 4)} for p, s in ranking(TOWN, damping)],
        "indegree": [{"page": p, "links_in": d} for p, d in indegree_ranking(TOWN)],
        "sweep": {"values": [0.0, 0.5, 0.85, 0.99], "scores": damping_sweep(TOWN, [0.0, 0.5, 0.85, 0.99])},
    }


@app.post("/rank")
def rank(g: Graph, damping: float = Query(0.85, ge=0, lt=1)) -> dict[str, object]:
    if len(g.links) > 200:
        raise HTTPException(422, "at most 200 pages")
    try:
        return {"pagerank": [{"page": p, "score": round(s, 4)} for p, s in ranking(g.links, damping)]}
    except RankError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
