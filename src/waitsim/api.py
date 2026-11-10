"""FastAPI app: simulate a clinic day, recommend staffing, compare with Erlang C."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from waitsim.erlang import mean_wait_min, offered_load, service_level
from waitsim.recommend import recommend
from waitsim.sim import Config, run_once, simulate

ROOT = Path(__file__).resolve().parents[2]

# A typical walk-in day: quiet start, mid-morning surge, lunchtime dip, afternoon bump.
SAMPLE_PROFILE = [0.0] * 8 + [0.8, 1.3, 1.6, 1.4, 0.8, 0.9, 1.2, 1.1] + [0.0] * 8


class ConfigIn(BaseModel):
    arrivals_per_hour: float = Field(default=12.0, gt=0, le=500)
    mean_service_min: float = Field(default=12.0, gt=0, le=240)
    servers: int = Field(default=4, ge=1, le=100)
    open_hour: int = Field(default=8, ge=0, le=23)
    close_hour: int = Field(default=16, ge=1, le=24)
    hourly_profile: list[float] = Field(default_factory=list, max_length=24)
    urgent_share: float = Field(default=0.0, ge=0, le=1)
    mean_patience_min: float = Field(default=0.0, ge=0, le=600)
    service_cv: float = Field(default=1.0, gt=0, le=3)

    def to_config(self) -> Config:
        return Config(
            self.arrivals_per_hour,
            self.mean_service_min,
            self.servers,
            self.open_hour,
            self.close_hour,
            tuple(self.hourly_profile),
            self.urgent_share,
            self.mean_patience_min,
            self.service_cv,
        )


class SimIn(BaseModel):
    config: ConfigIn = Field(default_factory=ConfigIn)
    replications: int = Field(default=30, ge=1, le=200)
    seed: int = Field(default=0, ge=0, le=100000)
    target_min: float = Field(default=30.0, gt=0, le=600)


class RecIn(SimIn):
    level: float = Field(default=0.9, gt=0, lt=1)


app = FastAPI(title="Waiting Room Simulator", version="1.0.0")


def _check(cfg: Config) -> None:
    try:
        cfg.validate()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return {
        "config": {
            "arrivals_per_hour": 12,
            "mean_service_min": 12,
            "servers": 3,
            "open_hour": 8,
            "close_hour": 16,
            "hourly_profile": SAMPLE_PROFILE,
            "urgent_share": 0.15,
            "mean_patience_min": 90,
            "service_cv": 1.0,
        },
        "replications": 30,
        "seed": 1,
        "target_min": 30,
        "level": 0.9,
    }


@app.post("/simulate")
def run_simulation(body: SimIn) -> dict[str, Any]:
    cfg = body.config.to_config()
    _check(cfg)
    prof = cfg.hourly_profile or (1.0,) * 24
    peak = cfg.arrivals_per_hour * max(prof)
    summary = simulate(cfg, body.replications, body.seed, body.target_min)
    load = offered_load(peak, cfg.mean_service_min)
    return {
        "summary": summary.__dict__,
        "peak_offered_load": round(load, 2),
        "peak_overloaded": load >= cfg.servers,
        "erlang_c_flat_peak": {
            "mean_wait_min": None
            if load >= cfg.servers
            else round(mean_wait_min(cfg.servers, peak, cfg.mean_service_min), 2),
            "share_within_target": round(service_level(cfg.servers, peak, cfg.mean_service_min, body.target_min), 3),
        },
    }


@app.post("/trace")
def trace(body: SimIn) -> dict[str, Any]:
    """One replication, patient by patient, so the UI can replay the day."""
    cfg = body.config.to_config()
    _check(cfg)
    r = run_once(cfg, body.seed, trace=True)
    rows = [
        {"arrive": round(a, 2), "start": round(s, 2), "end": round(e, 2), "urgent": u, "server": sv}
        for a, s, e, u, sv in sorted(r.trace)
    ]
    return {
        "servers": cfg.servers,
        "open": cfg.open_hour * 60,
        "close": cfg.close_hour * 60,
        "patients": rows,
        "walked_out": r.abandoned,
        "arrived": r.arrived,
    }


@app.post("/recommend")
def recommend_staffing(body: RecIn) -> dict[str, Any]:
    cfg = body.config.to_config()
    _check(cfg)
    return recommend(cfg, body.target_min, body.level, min(body.replications, 40), body.seed)


@app.get("/erlang")
def erlang(arrivals_per_hour: float, mean_service_min: float, servers: int, target_min: float = 30.0) -> dict[str, Any]:
    if arrivals_per_hour <= 0 or mean_service_min <= 0 or servers < 1:
        raise HTTPException(422, "arrivals, service time and servers must be positive")
    load = offered_load(arrivals_per_hour, mean_service_min)
    return {
        "offered_load": round(load, 3),
        "utilization": round(load / servers, 3),
        "stable": load < servers,
        "mean_wait_min": None
        if load >= servers
        else round(mean_wait_min(servers, arrivals_per_hour, mean_service_min), 3),
        "share_within_target": round(service_level(servers, arrivals_per_hour, mean_service_min, target_min), 3),
    }


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
