"""FastAPI app for the rate limiter lab."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import ALGORITHMS, RateError, compare, simulate, traffic

app = FastAPI(title="Rate Limiter Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/compare")
def compare_all(
    kind: str = "edge", limit: int = Query(10, ge=1, le=1000), window: float = Query(10.0, gt=0, le=3600),
    seed: int = 0,
) -> dict[str, object]:
    try:
        rows = compare(kind, limit, window, seed)
        times = traffic(kind, 60, seed)
        timeline = {n: simulate(n, times, limit, window) for n in ALGORITHMS}
    except RateError as e:
        raise HTTPException(422, str(e)) from e
    return {"rows": rows, "times": [round(t, 3) for t in times], "timeline": timeline}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
