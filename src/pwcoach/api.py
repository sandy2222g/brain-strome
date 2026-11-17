"""FastAPI app for the password coach. Passwords are analysed in memory and never stored or logged."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import PasswordError, assess, passphrase_bits

app = FastAPI(title="Password Strength Coach")
STATIC = Path(__file__).resolve().parents[2] / "static"


class Body(BaseModel):
    password: str = Field(min_length=1, max_length=128)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/assess")
def run(body: Body) -> dict[str, object]:
    try:
        r = assess(body.password)
    except PasswordError as e:
        raise HTTPException(422, str(e)) from e
    return {"score": r.score, "entropy_bits": r.entropy_bits, "crack_time": r.crack_time, "warnings": r.warnings}


@app.get("/passphrase")
def passphrase(words: int = 4) -> dict[str, float]:
    try:
        return {"entropy_bits": passphrase_bits(words)}
    except PasswordError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
