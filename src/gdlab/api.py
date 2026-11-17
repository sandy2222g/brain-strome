from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import GDError, closed_form, descend, experiment, make_data, mse

app = FastAPI(title="Gradient Descent Lab")
XS, YS = make_data()
W0, B0 = closed_form(XS, YS)
STATIC = Path(__file__).resolve().parents[2] / "static"
LRS = [0.0005, 0.002, 0.01, 0.03, 0.1, 0.5, 1.2]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data")
def data() -> dict[str, object]:
    return {"x": XS, "y": YS, "best": {"w": round(W0, 4), "b": round(B0, 4), "loss": round(mse(XS, YS, W0, B0), 4)},
            "lrs": LRS}


@app.get("/descend")
def run(lr: float = 0.03, steps: int = 400, scale: bool = False) -> dict[str, object]:
    try:
        r = descend(XS, YS, lr, steps, scale)
    except GDError as e:
        raise HTTPException(422, str(e)) from e
    return {"losses": [round(v, 4) for v in r.losses], "diverged": r.diverged, "steps_to_1pct": r.steps_to_1pct,
            "w": None if r.diverged else round(r.w, 4), "b": None if r.diverged else round(r.b, 4),
            "best_loss": round(mse(XS, YS, W0, B0), 4)}


@app.get("/experiment")
def table() -> dict[str, object]:
    return {"rows": experiment(XS, YS, LRS)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
