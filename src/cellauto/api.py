from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import PATTERNS, AutomataError, classify, life_run, rule_table, run_rule

app = FastAPI(title="Cellular Automata Lab")
STATIC = Path(__file__).resolve().parents[2] / "static"


@lru_cache(maxsize=1)
def table() -> list[dict[str, float]]:
    return rule_table()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/rule")
def rule(rule: int = 30, steps: int = 80, width: int = 161) -> dict[str, object]:
    try:
        rows = run_rule(rule, steps, width)
    except AutomataError as e:
        raise HTTPException(422, str(e)) from e
    stat = table()[rule]
    return {"rows": ["".join(map(str, r)) for r in rows], "density": stat["density"], "complexity": stat["complexity"]}


@app.get("/rules/top")
def top(n: int = 8) -> dict[str, object]:
    ranked = sorted(table(), key=lambda r: -r["complexity"])
    return {"top": ranked[:n], "bottom": sorted(table(), key=lambda r: r["complexity"])[:4]}


@app.get("/life")
def life(pattern: str = "glider", gens: int = 40) -> dict[str, object]:
    try:
        frames = life_run(pattern, min(gens, 200))
        info = classify(pattern)
    except AutomataError as e:
        raise HTTPException(422, str(e)) from e
    return {"frames": frames, "info": info}


@app.get("/patterns")
def patterns() -> dict[str, object]:
    return {"patterns": [classify(p) for p in PATTERNS]}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
