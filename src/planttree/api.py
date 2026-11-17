from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import FEATURES, LABELS, TreeError, accuracy, best_depth, evaluate, explain, fit, predict, rules, splits

app = FastAPI(title="Plant Watering Tree")
STATIC = Path(__file__).resolve().parents[2] / "static"
(TX, TY), (VX, VY), (SX, SY) = splits()
SCORES = evaluate()
BEST = best_depth(SCORES)
RANGES = {"soil_moisture": [5, 60], "days_since_watering": [0, 14], "sunlight_hours": [0, 12],
          "temperature_c": [12, 36]}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/info")
def info() -> dict[str, object]:
    t = fit(TX, TY, BEST)
    majority = max(SY.count(0), SY.count(1)) / len(SY)
    return {"features": FEATURES, "ranges": RANGES, "scores": SCORES, "best_depth": BEST,
            "test_accuracy": round(accuracy(t, SX, SY), 3), "majority_accuracy": round(majority, 3),
            "deep_test_accuracy": round(accuracy(fit(TX, TY, 8), SX, SY), 3)}


@app.get("/predict")
def run(soil_moisture: float, days_since_watering: float, sunlight_hours: float, temperature_c: float,
        depth: int = BEST) -> dict[str, object]:
    if not 0 <= depth <= 8:
        raise HTTPException(422, "depth must be 0-8")
    try:
        t = fit(TX, TY, depth)
    except TreeError as e:  # pragma: no cover
        raise HTTPException(422, str(e)) from e
    r = [soil_moisture, days_since_watering, sunlight_hours, temperature_c]
    return {"answer": LABELS[predict(t, r)], "why": explain(t, r), "rules": rules(t)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
