"""FastAPI app for the SMS spam filter."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from spamshield.core import DATA, NaiveBayes, evaluate, load_csv, split

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def state() -> dict[str, Any]:
    rows = load_csv(DATA / "messages.csv")
    train, test = split(rows)
    return {
        "model": NaiveBayes().fit(train),
        "test": test,
        "hard": load_csv(DATA / "hard_cases.csv"),
        "all_model": NaiveBayes().fit(rows),
    }


class PredictIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    threshold: float = Field(default=0.0, ge=-10, le=10)


app = FastAPI(title="SMS Spam Shield", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/examples")
def examples() -> list[dict[str, str]]:
    return [{"label": label, "text": text} for label, text in state()["hard"]]


@app.post("/predict")
def predict(body: PredictIn) -> dict[str, Any]:
    m: NaiveBayes = state()["all_model"]
    return {
        "label": m.predict(body.text, body.threshold),
        "spam_probability": round(m.prob_spam(body.text), 4),
        "log_odds": round(m.log_odds(body.text), 2),
        "reasons": [{"feature": f, "weight": w} for f, w in m.explain(body.text)],
    }


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    s = state()
    m: NaiveBayes = s["model"]
    return {
        "template_test": evaluate(m, s["test"]),
        "hard_cases": [{"threshold": t, **evaluate(m, s["hard"], t)} for t in (-4, -2, 0, 2)],
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
