"""FastAPI app for the heating schedule optimiser."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from heatplan.core import Day, House, load, optimise, simulate, thermostat

ROOT = Path(__file__).resolve().parents[2]
BASE = load()


class PlanIn(BaseModel):
    start_temp: float = Field(default=17.0, ge=5, le=30)
    comfort_target: float = Field(default=20.5, ge=15, le=26)
    thermostat_setpoint: float = Field(default=20.5, ge=15, le=26)


app = FastAPI(title="Heating Schedule Optimiser", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/day")
def day() -> dict[str, Any]:
    return {"outdoor": BASE.outdoor, "price": BASE.price, "comfort": BASE.comfort}


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    house = House(BASE.house.loss_per_h, BASE.house.heater_gain_c_per_h, BASE.house.heater_kw, body.start_temp)
    comfort = [(lo, hi, body.comfort_target if t > 19.5 else t) for lo, hi, t in BASE.comfort]
    d = Day(house, BASE.outdoor, BASE.price, comfort)
    best, base = optimise(d), thermostat(d, body.thermostat_setpoint)
    return {
        "optimised": {"schedule": best, **simulate(d, best)},
        "thermostat": {"schedule": base, **simulate(d, base)},
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
