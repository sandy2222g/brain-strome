"""FastAPI app: solve a morning run, compare with the naive plan, answer what-if questions, serve the page."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from busroutes.construct import naive_baseline, savings
from busroutes.evaluate import Plan, format_clock, plan_to_dict, summarise
from busroutes.instance import PlanningError, Problem, build_problem, generate, instance_to_dict
from busroutes.solver import solve

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "static"


class Params(BaseModel):
    seed: int = Field(default=7, ge=0, le=10_000)
    stops: int = Field(default=120, ge=10, le=400)
    buses: int = Field(default=8, ge=1, le=40)
    capacity: int = Field(default=36, ge=8, le=80)
    ride_limit_min: float = Field(default=45.0, ge=10, le=120)
    bell_min: int = Field(default=8 * 60 + 15, ge=5 * 60, le=11 * 60)
    close_roads: list[str] = Field(default_factory=list, max_length=10)


class Change(BaseModel):
    buses: int | None = Field(default=None, ge=1, le=40)
    capacity: int | None = Field(default=None, ge=8, le=80)
    ride_limit_min: float | None = Field(default=None, ge=10, le=120)
    close_roads: list[str] = Field(default_factory=list, max_length=10)


class WhatIf(BaseModel):
    base: Params = Field(default_factory=Params)
    change: Change


app = FastAPI(title="School Bus Route Planner", version="1.0.0")


@lru_cache(maxsize=64)
def _solved(
    seed: int, stops: int, buses: int, capacity: int, limit: float, bell: int, closed: tuple[str, ...]
) -> tuple[Problem, Plan]:
    inst = generate(seed, stops, buses, capacity, limit, bell).with_changes(close=closed)
    p = build_problem(inst)
    return p, solve(p)


def _run(par: Params) -> tuple[Problem, Plan]:
    try:
        return _solved(
            par.seed, par.stops, par.buses, par.capacity, par.ride_limit_min, par.bell_min, tuple(par.close_roads)
        )
    except PlanningError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _pct(before: float, after: float) -> float:
    return round(100 * (before - after) / before, 1) if before else 0.0


def _bundle(par: Params) -> dict[str, Any]:
    p, plan = _run(par)
    naive = naive_baseline(p)
    cw = savings(p)
    ours, base = summarise(p, plan), summarise(p, naive)
    return {
        "params": par.model_dump(),
        "town": instance_to_dict(p.inst),
        "plan": plan_to_dict(p, plan),
        "naive": plan_to_dict(p, naive)["summary"],
        "savings": summarise(p, cw),
        "comparison": {
            "km_saved_pct": _pct(base["total_km"], ours["total_km"]),
            "longest_ride_saved_min": round(base["longest_ride_min"] - ours["longest_ride_min"], 1),
            "late_stops_removed": base["stops_over_limit"] - ours["stops_over_limit"],
            "buses_saved": base["buses_used"] - ours["buses_used"],
        },
    }


def _delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, float]:
    keys = ["buses_used", "total_km", "total_minutes", "longest_ride_min", "stops_over_limit", "unserved_students"]
    return {k: round(after[k] - before[k], 2) for k in keys}


def _verdict(before: dict[str, Any], after: dict[str, Any], d: dict[str, float]) -> str:
    if after["unserved_students"]:
        return f"Not enough seats: {after['unserved_students']} students would be left at the kerb."
    if after["stops_over_limit"] > before["stops_over_limit"]:
        longest = after["longest_ride_min"]
        return f"{after['stops_over_limit']} stops would ride longer than the limit. Longest ride is {longest:.0f} min."
    if abs(d["total_km"]) < 0.05 and d["buses_used"] == 0 and abs(d["longest_ride_min"]) < 0.05:
        return "No change to the morning run."
    word = "adds" if d["total_km"] > 0 else "saves"
    return f"The run {word} {abs(d['total_km']):.1f} km and the longest ride moves {d['longest_ride_min']:+.1f} min."


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    out = _bundle(Params())
    out["start_clock"] = format_clock(out["params"]["bell_min"])
    return out


@app.post("/solve")
def solve_route(body: Params) -> dict[str, Any]:
    return _bundle(body)


@app.post("/whatif")
def whatif(body: WhatIf) -> dict[str, Any]:
    base_p, base_plan = _run(body.base)
    changed = body.base.model_copy(
        update={
            "buses": body.change.buses or body.base.buses,
            "capacity": body.change.capacity or body.base.capacity,
            "ride_limit_min": body.change.ride_limit_min or body.base.ride_limit_min,
            "close_roads": list(dict.fromkeys(body.base.close_roads + body.change.close_roads)),
        }
    )
    scen = _bundle(changed)
    before = summarise(base_p, base_plan)
    after = scen["plan"]["summary"]
    delta = _delta(before, after)
    return {
        "before": before,
        "after": after,
        "delta": delta,
        "verdict": _verdict(before, after, delta),
        "scenario": scen,
    }


if STATIC.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")
