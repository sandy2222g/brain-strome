"""FastAPI app."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Language Guesser")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Text(BaseModel):
    text: str


@lru_cache(maxsize=1)
def model() -> core.Model:
    return core.full_model()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/evaluation")
def evaluation() -> dict[str, object]:
    return core.evaluate()


@app.get("/examples")
def examples() -> dict[str, object]:
    corpus = core.load()
    return {"examples": [{"language": lang, "text": s[7]} for lang, s in corpus.items()]}


@app.post("/guess")
def guess(t: Text) -> dict[str, object]:
    try:
        return model().guess(t.text)
    except core.LangError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
