"""FastAPI app."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from . import core

app = FastAPI(title="Autocomplete Trie Search")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


@lru_cache(maxsize=1)
def trie() -> core.Trie:
    return core.load()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/suggest")
def suggest(q: str = Query(...), k: int = 5) -> dict[str, object]:
    try:
        return trie().suggest(q, k)
    except core.SearchError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/evaluation")
def evaluation() -> dict[str, float]:
    return core.evaluate()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
