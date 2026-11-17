"""FastAPI app for the k-means lab."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import KMeansError, blobs, compare_inits, elbow, kmeans

app = FastAPI(title="k-means Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"
DATA = blobs(60, seed=1)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/cluster")
def cluster(k: int = Query(4, ge=1, le=10), init: str = "pp", seed: int = 0) -> dict[str, object]:
    try:
        r = kmeans(DATA, k, init, seed)
    except KMeansError as e:
        raise HTTPException(422, str(e)) from e
    return {"points": [list(p) for p in DATA], "centres": [list(c) for c in r["centres"]],  # type: ignore[attr-defined]
            "labels": r["labels"], "inertia": round(float(r["inertia"]), 1), "iterations": r["iterations"]}  # type: ignore[arg-type]


_SUMMARY: dict[str, object] = {}


@app.get("/summary")
def summary() -> dict[str, object]:
    if not _SUMMARY:
        _SUMMARY.update({"elbow": [round(x, 1) for x in elbow(DATA)], "inits": compare_inits(DATA)})
    return dict(_SUMMARY)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
