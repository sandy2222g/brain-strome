"""FastAPI app."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from . import core

app = FastAPI(title="Cron Explainer")
STATIC = Path(__file__).resolve().parents[2] / "static" / "index.html"
DEFAULT_START = "2026-11-17T12:00:00"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/examples")
def examples() -> dict[str, object]:
    return {"examples": core.examples(), "start": DEFAULT_START}


@app.get("/explain")
def explain(expr: str, start: str = DEFAULT_START, n: int = 5) -> dict[str, object]:
    try:
        after = datetime.fromisoformat(start)
        runs = core.next_runs(expr, after, n)
        return {"expr": expr, "meaning": core.explain(expr), "start": start,
                "runs": [r.strftime("%Y-%m-%d %H:%M %a") for r in runs]}
    except (core.CronError, ValueError) as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC)
