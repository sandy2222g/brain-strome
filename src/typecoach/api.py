"""FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import core

app = FastAPI(title="Typing Speed Coach")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"


class Attempt(BaseModel):
    target: str
    typed: str
    seconds: float


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, object]:
    return {"sessions": core.load_sessions()}


@app.get("/evaluation")
def evaluation() -> dict[str, object]:
    return core.evaluate()


@app.post("/analyse")
def analyse(a: Attempt) -> dict[str, object]:
    try:
        return core.analyse(a.target, a.typed, a.seconds)
    except core.TypingError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/coach")
def coach() -> dict[str, object]:
    results = [core.analyse(str(s["target"]), str(s["typed"]), float(s["seconds"]))  # type: ignore[arg-type]
               for s in core.load_sessions()]
    weak = core.weak_keys(results)
    return {"weak_keys": weak, "drill": core.drill([str(w["key"]) for w in weak[:3]], core.load_words()),
            "net_wpm": [r["net_wpm"] for r in results]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
