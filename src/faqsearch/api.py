"""FastAPI app for the campus FAQ search."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from faqsearch.core import Index, SearchError, evaluate, load

ROOT = Path(__file__).resolve().parents[2]
INDEX = Index(load()["faqs"])


class In(BaseModel):
    query: str = Field(min_length=1, max_length=300)


app = FastAPI(title="Campus FAQ Search", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return evaluate()


@app.post("/search")
def run(body: In) -> dict[str, Any]:
    try:
        return {"results": INDEX.search(body.query)}
    except SearchError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
