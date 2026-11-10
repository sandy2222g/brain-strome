"""FastAPI application: calculator, levers, plan builder and a static single page."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from carbon.calculator import CATEGORIES, LABELS, calculate, typical_answers
from carbon.factors import DISCLAIMER, default_factors
from carbon.levers import rank_levers
from carbon.model import CarbonModel, load_dataset
from carbon.plan import MAX_PLAN, PlanError, build_plan, suggest_plan
from carbon.schema import FIELD_LABELS, Answers
from carbon.synth import DATA_PATH, ROOT

MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "carbon.joblib"))
SAMPLE_PATH = ROOT / "data" / "sample_household.json"
STATIC_DIR = ROOT / "static"


class AnswersIn(BaseModel):
    answers: Answers


class PlanIn(BaseModel):
    answers: Answers
    lever_ids: list[str] = Field(default_factory=list, max_length=MAX_PLAN)


def get_model() -> CarbonModel:
    """Load the persisted model; train from the bundled synthetic survey on first start."""
    if MODEL_PATH.exists():
        return CarbonModel.load(MODEL_PATH)
    model = CarbonModel().fit(load_dataset(DATA_PATH))
    try:
        model.save(MODEL_PATH)
        (MODEL_PATH.parent / "metrics.json").write_text(json.dumps(model.metrics, indent=2), encoding="utf-8")
    except OSError:  # read-only filesystem: keep it in memory
        pass
    return model


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    app.state.model = get_model()
    yield


app = FastAPI(title="Household Carbon Coach", version="1.0.0", lifespan=lifespan)


def _model() -> CarbonModel:
    return app.state.model  # type: ignore[no-any-return]


def footprint_report(answers: Answers, model: CarbonModel) -> dict[str, Any]:
    full, filled = model.fill(answers)
    fp = calculate(full)
    typical = calculate(typical_answers(answers.household_size))
    categories = []
    for key in CATEGORIES:
        kg, tkg = fp.by_category_kg[key], typical.by_category_kg[key]
        categories.append(
            {
                "key": key,
                "label": LABELS[key],
                "kg": round(kg, 1),
                "t": round(kg / 1000, 3),
                "share_pct": round(100 * kg / fp.total_kg, 1) if fp.total_kg else 0.0,
                "typical_t": round(tkg / 1000, 3),
                "diff_t": round((kg - tkg) / 1000, 3),
            }
        )
    return {
        "total_t": round(fp.total_t, 2),
        "per_person_t": round(fp.total_t / answers.household_size, 2),
        "typical_t": round(typical.total_t, 2),
        "vs_typical_pct": round(100 * (fp.total_kg - typical.total_kg) / typical.total_kg, 1),
        "categories": categories,
        "peers": {
            "percentile": model.peer_percentile(fp.total_t, answers.household_size),
            "basis": "tonnes per person among synthetic households",
            "n": len(model.reference_per_person),
        },
        "estimate": model.estimate(answers),
        "uses_estimates": bool(filled),
        "filled": [
            {"field": k, "label": FIELD_LABELS[k][0], "value": v, "unit": FIELD_LABELS[k][1]} for k, v in filled.items()
        ],
        "answers_used": full.model_dump(),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "model_loaded": hasattr(app.state, "model")}


@app.get("/factors")
def factors() -> dict[str, Any]:
    rows = [
        {"key": r.key, "category": r.category, "value": r.value, "unit": r.unit, "note": r.note}
        for r in default_factors().rows
    ]
    return {"disclaimer": DISCLAIMER, "count": len(rows), "factors": rows}


@app.post("/footprint")
def footprint(body: AnswersIn) -> dict[str, Any]:
    return footprint_report(body.answers, _model())


@app.post("/levers")
def levers(body: AnswersIn) -> dict[str, Any]:
    full, _ = _model().fill(body.answers)
    ranked = rank_levers(full)
    return {
        "baseline_t": round(calculate(full).total_t, 2),
        "ordered_by": "tonnes saved per year divided by effort (1 to 5)",
        "levers": [r.__dict__ for r in ranked],
    }


@app.post("/plan")
def plan(body: PlanIn) -> dict[str, Any]:
    full, _ = _model().fill(body.answers)
    ids = body.lever_ids
    suggested = False
    if not ids:
        ids, suggested = suggest_plan(full), True
    try:
        result = build_plan(full, ids)
    except PlanError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "suggested": suggested,
        "lever_ids": ids,
        "baseline_t": result.baseline_t,
        "after_t": result.after_t,
        "saved_t": result.saved_t,
        "saved_pct": result.saved_pct,
        "interaction_t": result.interaction_t,
        "steps": [s.__dict__ for s in result.steps],
        "after_categories": [
            {"key": k, "label": LABELS[k], "t": round(v / 1000, 3)} for k, v in result.after_by_category_kg.items()
        ],
    }


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return {"trained_on": "synthetic household survey, seeded generator, CC0", **_model().metrics}


@app.get("/sample")
def sample() -> dict[str, Any]:
    raw = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    answers = Answers(**raw["answers"])
    return {"name": raw["name"], "answers": raw["answers"], "footprint": footprint_report(answers, _model())}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
