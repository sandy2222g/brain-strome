from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import MakerError, best_order, evaluate, generate, load_names

app = FastAPI(title="Markov Name Maker")
NAMES = load_names()
STATIC = Path(__file__).resolve().parents[2] / "static"
SCORES = evaluate(NAMES)
BEST = best_order(NAMES)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/scores")
def scores() -> dict[str, object]:
    return {"scores": SCORES, "best": BEST, "names": len(NAMES)}


@app.get("/generate")
def make(n: int = 8, order: int = BEST, seed: int = 0, prefix: str = "") -> dict[str, object]:
    if not 0 <= order <= 4:
        raise HTTPException(422, "order must be 0-4")
    try:
        b = generate(NAMES, order, n, seed, prefix)
    except MakerError as e:
        raise HTTPException(422, str(e)) from e
    return {"names": b.names, "order": order, "attempts": b.attempts}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
