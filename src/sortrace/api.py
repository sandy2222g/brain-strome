from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import ALGOS, KINDS, SortError, make_input, run, table, thin

app = FastAPI(title="Sorting Race")
STATIC = Path(__file__).resolve().parents[2] / "static"
TABLE = table(200)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/options")
def options() -> dict[str, object]:
    return {"kinds": KINDS, "algos": ALGOS, "table": TABLE, "table_n": 200}


@app.get("/race")
def race(kind: str = "random", n: int = 30, seed: int = 1) -> dict[str, object]:
    if n > 60:
        raise HTTPException(422, "animation is limited to 60 items")
    try:
        data = make_input(kind, n, seed)
        lanes = {}
        for a in ALGOS:
            t = run(a, data)
            lanes[a] = {"comparisons": t.comparisons, "writes": t.writes,
                        "frames": [[c, arr] for c, arr in thin(t.frames)]}
    except SortError as e:
        raise HTTPException(422, str(e)) from e
    return {"input": data, "lanes": lanes, "max_comparisons": max(v["comparisons"] for v in lanes.values())}  # type: ignore[type-var]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
