"""FastAPI app: upload a statement, get recurring charges, savings and price hikes."""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from sniffer.categorize import CategoryModel
from sniffer.detect import Txn
from sniffer.evaluate import evaluate
from sniffer.io import StatementError, parse_csv
from sniffer.report import analyze

ROOT = Path(__file__).resolve().parents[1].parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "category.joblib"))
DATA = ROOT / "data"
MAX_BYTES = 2_000_000


class TxnIn(BaseModel):
    date: str
    description: str = Field(min_length=1, max_length=200)
    amount: float


class StatementIn(BaseModel):
    transactions: list[TxnIn] = Field(min_length=1, max_length=20000)


def get_model() -> CategoryModel:
    if MODEL_PATH.exists():
        return CategoryModel.load(MODEL_PATH)
    m = CategoryModel()
    m.fit(pd.read_csv(DATA / "merchants.csv"))
    try:
        m.save(MODEL_PATH)
    except OSError:
        pass
    return m


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.cats = get_model()
    app.state.eval = evaluate(DATA / "transactions.csv")
    yield


app = FastAPI(title="Subscription Sniffer", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return {**app.state.cats.metrics, **app.state.eval}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return analyze(parse_csv((DATA / "transactions.csv").read_text()), app.state.cats)


@app.post("/analyze")
def analyze_json(body: StatementIn) -> dict[str, Any]:
    csv_text = "date,description,amount\n" + "\n".join(
        f'{t.date},"{t.description.replace(chr(34), "")}",{t.amount}' for t in body.transactions
    )
    try:
        return analyze(parse_csv(csv_text), app.state.cats)
    except StatementError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/analyze/csv")
async def analyze_csv(file: UploadFile = File(...)) -> dict[str, Any]:  # noqa: B008
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "file larger than 2 MB")
    try:
        return analyze(parse_csv(raw.decode("utf-8", errors="replace")), app.state.cats)
    except StatementError as exc:
        raise HTTPException(422, str(exc)) from exc


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


__all__ = ["app", "Txn"]
