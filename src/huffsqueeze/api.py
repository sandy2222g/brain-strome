"""FastAPI app for Huffman squeeze."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import HuffmanError, analyse

app = FastAPI(title="Huffman Squeeze")
STATIC = Path(__file__).resolve().parents[2] / "static"
SAMPLES = {
    "pangram": "the quick brown fox jumps over the lazy dog",
    "repetitive": "abababababababababababababababababababab" * 5,
    "song": "row row row your boat gently down the stream merrily merrily merrily merrily life is but a dream " * 3,
}


class Body(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/samples")
def samples() -> dict[str, dict[str, str]]:
    return {"samples": SAMPLES}


@app.post("/analyse")
def run(body: Body) -> dict[str, object]:
    try:
        return analyse(body.text)
    except HuffmanError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
