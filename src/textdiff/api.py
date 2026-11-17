from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .core import diff_lines, distance, pair_changes, samples

app = FastAPI(title="Text Diff Viewer")
STATIC = Path(__file__).resolve().parents[2] / "static"
LIMIT = 4000  # lines per side: the trace grows with edits, so keep requests bounded


class Req(BaseModel):
    a: str = Field(max_length=200_000)
    b: str = Field(max_length=200_000)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, str]:
    return samples()


@app.post("/diff")
def diff(r: Req) -> dict[str, object]:
    if len(r.a.splitlines()) > LIMIT or len(r.b.splitlines()) > LIMIT:
        raise HTTPException(422, f"limit is {LIMIT} lines per side")
    ops = diff_lines(r.a, r.b)
    rows = pair_changes(ops)
    return {"rows": rows, "edits": distance(ops),
            "added": sum(o.kind == "add" for o in ops), "deleted": sum(o.kind == "del" for o in ops)}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
