"""FastAPI app: /health, /sample, /solve, /swap-check and the static roster board."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .generator import generate
from .model import Assignment, Problem, compile_problem
from .report import solve_problem
from .swap import swap_check

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
STATIC = ROOT / "static"

app = FastAPI(title="Fair Shift Roster", version=__version__)


class SolveRequest(BaseModel):
    problem: Problem | None = None
    seed: int = Field(default=7, ge=0, le=1_000_000)
    iterations: int | None = Field(default=None, ge=0, le=250_000)


class Cell(BaseModel):
    staff_id: str
    day: int = Field(ge=0, le=27)


class SwapRequest(BaseModel):
    problem: Problem | None = None
    assignments: list[Assignment] = Field(max_length=2000)
    a: Cell
    b: Cell


def sample_problem(weeks: int = 1) -> Problem:
    path = DATA / ("sample_week.json" if weeks == 1 else "sample_4weeks.json")
    if path.exists():
        return Problem.model_validate(json.loads(path.read_text()))
    return generate(2024, weeks)


_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/sample")
def sample(weeks: int = Query(default=1)) -> dict[str, Any]:
    if weeks not in (1, 4):
        raise HTTPException(422, "weeks must be 1 or 4")
    return sample_problem(weeks).model_dump()


@app.post("/solve")
def solve(req: SolveRequest) -> dict[str, Any]:
    problem = req.problem or sample_problem(1)
    key = f"{problem.model_dump_json()}|{req.seed}|{req.iterations}"
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    result = solve_problem(problem, req.seed, req.iterations)
    _cache[key] = result
    while len(_cache) > 16:
        _cache.popitem(last=False)
    return result


@app.post("/swap-check")
def swap(req: SwapRequest) -> dict[str, Any]:
    problem = req.problem or sample_problem(1)
    inst = compile_problem(problem)
    try:
        return swap_check(inst, req.assignments, (req.a.staff_id, req.a.day), (req.b.staff_id, req.b.day))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")
