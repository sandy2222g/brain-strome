from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import SCHEMES, CheckError, clean, experiment, validate

app = FastAPI(title="Check Digit Validator")
STATIC = Path(__file__).resolve().parents[2] / "static"
EXAMPLES = {"luhn": "4111 1111 1111 1111", "isbn10": "0-306-40615-2", "isbn13": "978-0-306-40615-7",
            "iban": "GB82 WEST 1234 5698 7654 32"}


@lru_cache(maxsize=4)
def cached(trials: int) -> dict[str, dict[str, float]]:
    return experiment(trials)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/validate")
def check(scheme: str, value: str) -> dict[str, object]:
    if len(value) > 60:
        raise HTTPException(422, "value is too long")
    try:
        ok = validate(scheme, value)
    except CheckError as e:
        raise HTTPException(422, str(e)) from e
    return {"scheme": scheme, "value": clean(value), "valid": ok}


@app.get("/examples")
def examples() -> dict[str, object]:
    return {"schemes": SCHEMES, "examples": EXAMPLES}


@app.get("/experiment")
def run(trials: int = 4000) -> dict[str, object]:
    try:
        return {"trials": trials, "rates": cached(trials)}
    except CheckError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
