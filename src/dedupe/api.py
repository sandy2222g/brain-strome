"""FastAPI app for the contact deduplicator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from dedupe.core import Contact, evaluate, find_duplicates, merge

ROOT = Path(__file__).resolve().parents[2]


class ContactIn(BaseModel):
    id: int
    name: str = Field(max_length=80)
    phone: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)
    group: int | None = None


class DedupeIn(BaseModel):
    contacts: list[ContactIn] = Field(max_length=5000)
    threshold: float = Field(default=0.8, ge=0.5, le=1.0)


app = FastAPI(title="Contact Dedupe", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "contacts.json").read_text())


@app.post("/dedupe")
def run(body: DedupeIn) -> dict[str, Any]:
    cs = [Contact(c.id, c.name, c.phone, c.email) for c in body.contacts]
    by_id = {c.id: c for c in cs}
    clusters = find_duplicates(cs, body.threshold)
    out: dict[str, Any] = {
        "clusters": [
            {"ids": ids, "members": [by_id[i].__dict__ for i in ids], "merged": merge([by_id[i] for i in ids]).__dict__}
            for ids in clusters
        ],
        "total": len(cs),
        "after_merge": len(cs) - sum(len(c) - 1 for c in clusters),
    }
    labels = {c.id: c.group for c in body.contacts if c.group is not None}
    if len(labels) == len(cs) and cs:
        out["evaluation"] = evaluate(labels, clusters)
    return out


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
