"""FastAPI application exposing the triage model and a small web UI."""
from __future__ import annotations

import csv
import io
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from triage.model import PRIORITY_ORDER, TriageModel, load_dataset

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "triage.joblib"))
DATA_PATH = ROOT / "data" / "tickets.csv"
MAX_BATCH = 500


class TicketIn(BaseModel):
    subject: str = Field(default="", max_length=300)
    body: str = Field(min_length=1, max_length=5000)


class TicketOut(BaseModel):
    category: str
    category_confidence: float
    priority: str
    priority_confidence: float
    sla_hours: int
    top_terms: list[str]


def get_model() -> TriageModel:
    """Load the persisted model; train from bundled sample data on first start."""
    if MODEL_PATH.exists():
        return TriageModel.load(MODEL_PATH)
    model = TriageModel()
    model.fit(load_dataset(DATA_PATH))
    try:
        model.save(MODEL_PATH)
    except OSError:  # read-only filesystem: keep it in memory
        pass
    return model


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    app.state.model = get_model()
    yield


app = FastAPI(title="Support Ticket Triage", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    m = dict(app.state.model.metrics)
    m.pop("category_report", None)
    m.pop("priority_report", None)
    return m


@app.post("/predict", response_model=TicketOut)
def predict(ticket: TicketIn) -> TicketOut:
    pred = app.state.model.predict(ticket.subject, ticket.body)
    return TicketOut(**pred.__dict__)


@app.post("/predict/batch")
async def predict_batch(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
    """CSV with `subject` and `body` columns -> tickets sorted by urgency."""
    raw = (await file.read()).decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or "body" not in reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV must contain a 'body' column")
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=422, detail="CSV has no rows")
    if len(rows) > MAX_BATCH:
        raise HTTPException(status_code=413, detail=f"max {MAX_BATCH} rows per request")
    items = [((r.get("subject") or ""), (r.get("body") or "")) for r in rows]
    preds = app.state.model.predict_batch(items)
    results = [
        {"subject": s, "body": b, **p.__dict__} for (s, b), p in zip(items, preds, strict=True)
    ]
    results.sort(key=lambda r: (-PRIORITY_ORDER.index(r["priority"]), -r["priority_confidence"]))
    return {"count": len(results), "results": results}


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")
