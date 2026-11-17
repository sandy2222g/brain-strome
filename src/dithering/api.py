from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import METHODS, DitherError, blur_error, brightness_gap, compare, dither, images

app = FastAPI(title="Dither Lab")
IMAGES = images()
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/images")
def list_images() -> dict[str, object]:
    return {"images": list(IMAGES), "methods": list(METHODS)}


@app.get("/dither")
def run(image: str = "sphere", method: str = "floyd-steinberg") -> dict[str, object]:
    if image not in IMAGES:
        raise HTTPException(404, f"image must be one of {', '.join(IMAGES)}")
    try:
        bits = dither(IMAGES[image], method)
    except DitherError as e:
        raise HTTPException(422, str(e)) from e
    src = IMAGES[image]
    return {"bits": ["".join(map(str, r)) for r in bits], "grey": [[round(v, 3) for v in r] for r in src],
            "blur_error": round(blur_error(src, bits), 4), "brightness_gap": round(brightness_gap(src, bits), 4),
            "table": compare(src)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
