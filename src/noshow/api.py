"""FastAPI app: single-appointment risk, whole-day planning, metrics, UI."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from noshow.model import NoShowModel, load_dataset

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "noshow.joblib"))
DATA_PATH = ROOT / "data" / "appointments.csv"


class Appointment(BaseModel):
    age: int = Field(ge=0, le=120)
    lead_days: int = Field(ge=0, le=365, description="days between booking and appointment")
    prior_visits: int = Field(ge=0, le=500)
    prior_noshows: int = Field(ge=0, le=500)
    hour: int = Field(ge=0, le=23)
    weekday: int = Field(ge=0, le=6, description="0=Monday")
    reminder_sent: int = Field(ge=0, le=1)
    distance_km: float = Field(ge=0, le=500)
    insurance: Literal["public", "private", "none"]


class DayPlanIn(BaseModel):
    appointments: list[Appointment] = Field(min_length=1, max_length=300)


def get_model() -> NoShowModel:
    if MODEL_PATH.exists():
        return NoShowModel.load(MODEL_PATH)
    model = NoShowModel()
    model.fit(load_dataset(DATA_PATH))
    try:
        model.save(MODEL_PATH)
    except OSError:
        pass
    return model


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    app.state.model = get_model()
    yield


app = FastAPI(title="Clinic No-Show Predictor", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return dict(app.state.model.metrics)


@app.post("/predict")
def predict(appt: Appointment) -> dict[str, Any]:
    pred = app.state.model.predict(appt.model_dump())
    return {"probability": pred.probability, "band": pred.band, "action": pred.action}


@app.post("/plan-day")
def plan_day(body: DayPlanIn) -> dict[str, Any]:
    return app.state.model.plan_day([a.model_dump() for a in body.appointments])


@app.get("/sample-day")
def sample_day() -> DayPlanIn:
    """A small canned schedule so the UI works without any input."""
    df = load_dataset(DATA_PATH).drop(columns=["no_show"]).head(20)
    return DayPlanIn(appointments=[Appointment(**r) for r in df.to_dict("records")])


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
