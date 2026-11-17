from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import LadderError, bfs, bidirectional, examples, load_words

app = FastAPI(title="Word Ladder Solver")
WORDS = load_words()
STATIC = Path(__file__).resolve().parents[2] / "static"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/examples")
def get_examples() -> dict[str, object]:
    return {"examples": examples(), "words": len(WORDS)}


@app.get("/ladder")
def ladder(a: str, z: str) -> dict[str, object]:
    try:
        fast = bidirectional(a, z, WORDS)
        plain = bfs(a, z, WORDS)
    except LadderError as e:
        raise HTTPException(422, str(e)) from e
    if fast is None or plain is None:
        return {"found": False, "path": [], "steps": 0, "explored": 0, "plain_explored": 0}
    return {"found": True, "path": fast.path, "steps": len(fast.path) - 1,
            "explored": fast.explored, "plain_explored": plain.explored}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
