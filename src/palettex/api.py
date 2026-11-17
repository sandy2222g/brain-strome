"""FastAPI app for the palette extractor."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from palettex.core import SAMPLE, PaletteError, extract, pixels_from_bytes

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="Palette Extractor", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/palette")
async def palette(
    k: Annotated[int, Form()] = 5,
    file: Annotated[UploadFile | None, File()] = None,
) -> dict[str, Any]:
    """Palette of the uploaded image, or of the bundled sample when no file is sent."""
    try:
        data = await file.read() if file else SAMPLE.read_bytes()
        return extract(pixels_from_bytes(data), k)
    except PaletteError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
