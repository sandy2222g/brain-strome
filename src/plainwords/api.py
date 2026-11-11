"""FastAPI app for the plain-language checker."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from plainwords.core import TextError, review

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = (
    "Pursuant to the terms of your tenancy, residents are requested to utilize the designated bins in order to "
    "facilitate collection, and additional charges will be applied in the event that sufficient notice is not given "
    "prior to the commencement of works at this point in time, notwithstanding any assistance previously rendered.\n\n"
    "Please put your rubbish in the bins by the gate. We empty them on Tuesdays. Call us if you need help."
)


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)


app = FastAPI(title="Plain Words Checker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, str]:
    return {"text": SAMPLE}


@app.post("/review")
def run(body: TextIn) -> dict[str, Any]:
    try:
        return review(body.text)
    except TextError as err:
        raise HTTPException(422, str(err)) from err


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
