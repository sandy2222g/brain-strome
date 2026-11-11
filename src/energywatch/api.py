"""FastAPI app for the home energy anomaly detector."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from energywatch.core import Reading, alerts, evaluate, fit, load, naive_alerts, score

ROOT = Path(__file__).resolve().parents[2]
TRAIN_DAYS = 14


@lru_cache(maxsize=1)
def state() -> dict[str, Any]:
    rows = load()
    train = [r for r in rows if r.day < TRAIN_DAYS]
    test = [r for r in rows if r.day >= TRAIN_DAYS]
    return {"train": train, "test": test, "model": fit(train)}


def _alert_row(a: Any) -> dict[str, Any]:
    return {"day": a.day, "start": a.start, "hours": a.hours, "peak_score": a.peak_score, "direction": a.direction}


app = FastAPI(title="Home Energy Anomaly Watch", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/analyse")
def analyse(
    threshold: float = Query(default=4.0, ge=1.0, le=12.0), min_run: int = Query(default=2, ge=1, le=6)
) -> dict[str, Any]:
    s = state()
    test: list[Reading] = s["test"]
    found = alerts(s["model"], test, threshold, min_run)
    naive = naive_alerts(s["train"], test)
    return {
        "first_day": TRAIN_DAYS,
        "cells": [
            {"day": r.day, "hour": r.hour, "kwh": r.kwh, "score": round(score(s["model"], r), 2), "fault": r.fault}
            for r in test
        ],
        "alerts": [_alert_row(a) for a in found],
        "eval": evaluate(test, found),
        "naive_eval": evaluate(test, naive),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
