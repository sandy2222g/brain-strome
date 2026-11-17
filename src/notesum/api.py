"""FastAPI app for the meeting notes summarizer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from notesum.core import NotesError, action_items, evaluate, lead_k, load, sentences, summarise

ROOT = Path(__file__).resolve().parents[2]


class In(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    k: int = Field(default=3, ge=1, le=10)


app = FastAPI(title="Meeting Notes Summarizer", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return load()


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return evaluate()


@app.post("/summarise")
def run(body: In) -> dict[str, Any]:
    try:
        sents = sentences(body.text)
        s = summarise(body.text, body.k)
        return {
            "sentences": sents,
            "chosen": s["indices"],
            "summary": s["summary"],
            "lead_baseline": lead_k(body.text, body.k),
            "actions": action_items(body.text),
        }
    except NotesError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
