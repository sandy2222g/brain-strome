"""FastAPI app: classify a hand-drawn 8x8 digit."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from digitpad.core import (
    DigitError,
    accuracy,
    baseline_logreg,
    confusion,
    fit,
    shifted_accuracy,
    split,
    validate,
)

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def state() -> dict[str, Any]:
    x_train, x_test, y_train, y_test = split()
    clf = fit(x_train, y_train, True)
    plain = fit(x_train, y_train, False)
    return {
        "clf": clf,
        "x_test": x_test,
        "y_test": y_test,
        "metrics": {
            "accuracy": round(accuracy(clf, x_test, y_test), 3),
            "accuracy_without_centring": round(accuracy(plain, x_test, y_test), 3),
            "shifted_accuracy": round(shifted_accuracy(clf, x_test, y_test), 3),
            "shifted_accuracy_without_centring": round(shifted_accuracy(plain, x_test, y_test), 3),
            "logistic_regression_accuracy": round(baseline_logreg(x_train, y_train, x_test, y_test), 3),
            "test_images": int(len(y_test)),
            "confusion": confusion(clf, x_test, y_test),
        },
    }


class DrawIn(BaseModel):
    pixels: list[float] = Field(min_length=64, max_length=64)


app = FastAPI(title="Digit Sketchpad", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return state()["metrics"]


@app.get("/samples")
def samples() -> list[dict[str, Any]]:
    s = state()
    seen: dict[int, int] = {}
    out = []
    for i, label in enumerate(s["y_test"]):
        if int(label) not in seen:
            seen[int(label)] = i
            out.append({"label": int(label), "pixels": [float(v) for v in s["x_test"][i].ravel()]})
    return sorted(out, key=lambda d: d["label"])


@app.post("/predict")
def predict(body: DrawIn) -> dict[str, Any]:
    try:
        img = validate(body.pixels)
    except DigitError as err:
        raise HTTPException(422, str(err)) from err
    p = state()["clf"].proba(img)
    top = int(np.argmax(p))
    return {"digit": top, "confidence": round(float(p[top]), 3), "probabilities": [round(float(v), 3) for v in p]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
