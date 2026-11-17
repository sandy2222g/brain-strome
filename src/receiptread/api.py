"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Receipt Line Reader")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Receipt(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/samples")
def samples() -> dict[str, object]:
    return {"samples": [{"id": r["id"], "text": r["text"]} for r in core.load()]}


@app.get("/evaluation")
def evaluation() -> dict[str, object]:
    return core.evaluate()


@app.post("/parse")
def parse(r: Receipt) -> dict[str, object]:
    try:
        return core.parse(r.text)
    except core.ReceiptError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
