"""FastAPI app: balances and minimal settlement for shared expenses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from settler.core import Expense, SettleError, balances, naive_payments, settle

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "sample_flat.json"


class ExpenseIn(BaseModel):
    label: str = Field(default="", max_length=60)
    payer: str = Field(min_length=1, max_length=30)
    amount: float = Field(gt=0, le=100000)
    split_among: list[str] = Field(min_length=1, max_length=30)


class SettleIn(BaseModel):
    expenses: list[ExpenseIn] = Field(min_length=1, max_length=500)


app = FastAPI(title="Roommate Bill Settler", version="1.0.0")


def _pay(p: Any) -> dict[str, Any]:
    return {"from": p.frm, "to": p.to, "amount": p.cents / 100}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample")
def sample() -> dict[str, Any]:
    return json.loads(SAMPLE.read_text())


@app.post("/settle")
def run(body: SettleIn) -> dict[str, Any]:
    exps = [Expense(e.payer, round(e.amount * 100), tuple(e.split_among), e.label) for e in body.expenses]
    try:
        net = balances(exps)
        plan = settle(net)
    except SettleError as err:
        raise HTTPException(422, str(err)) from err
    naive = naive_payments(exps)
    return {
        "balances": {k: v / 100 for k, v in sorted(net.items())},
        "payments": [_pay(p) for p in plan],
        "naive_count": len(naive),
        "payment_count": len(plan),
        "total_spent": sum(e.cents for e in exps) / 100,
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
