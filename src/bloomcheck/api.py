from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .core import STRICT_P, BloomError, cached, check_text, load_words, set_bytes

app = FastAPI(title="Bloom Spellcheck")
STATIC = Path(__file__).resolve().parents[2] / "static"
SAMPLE = "The quik brown dog wnet to the scool and sang a song about the moun in the nigt."


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, str]:
    return {"text": SAMPLE}


@app.get("/check")
def check(text: str, p: float = 0.01) -> dict[str, object]:
    if len(text) > 5000:
        raise HTTPException(422, "text is limited to 5000 characters")
    try:
        b, fp = cached(round(p, 6))
    except BloomError as e:
        raise HTTPException(422, str(e)) from e
    words = load_words()
    found = check_text(text, b, cached(STRICT_P)[0])
    return {"unknown": [{"word": f.word, "suggestions": f.suggestions} for f in found],
            "filter": {"bits": b.m, "hashes": b.k, "bytes": b.nbytes, "set_bytes": set_bytes(words),
                       "words": b.count, "expected_fp": round(b.expected_fp(), 5), "measured_fp": round(fp, 5)}}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
