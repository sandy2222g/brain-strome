"""FastAPI app: JSON endpoints plus the single static page."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from rentcheck import __version__
from rentcheck.advice import find_alternatives, negotiation_hint, verdict
from rentcheck.config import CURRENCY, MODEL_PATH, STATIC_DIR
from rentcheck.model import RentModel
from rentcheck.schemas import ListingIn
from rentcheck.train import train

app = FastAPI(title="rent-check", version=__version__, description="Is my rent fair? Synthetic-city demo.")

SAMPLE: dict[str, Any] = {
    "district": "Linden Park",
    "bedrooms": 2,
    "bathrooms": 1,
    "size_m2": 58,
    "floor": 3,
    "furnished": False,
    "balcony": True,
    "lift": True,
    "building_age": 22,
    "dist_centre_km": 2.6,
    "dist_metro_km": 0.6,
    "pets_allowed": True,
}


@lru_cache(maxsize=1)
def get_model() -> RentModel:
    """Load the trained model, training it first if the file is missing."""
    return RentModel.load() if MODEL_PATH.exists() else train()


@app.get("/health")
def health() -> dict[str, str]:
    get_model()
    return {"status": "ok", "version": __version__}


@app.get("/metrics")
def metrics() -> dict[str, Any]:
    return {"currency": CURRENCY, **get_model().metrics}


@app.get("/districts")
def districts() -> dict[str, Any]:
    return {"currency": CURRENCY, "districts": get_model().district_table()}


@app.get("/sample")
def sample() -> dict[str, Any]:
    """A worked example: a typical Linden Park flat priced about 15% over the market."""
    m = get_model()
    r = m.estimate_range(SAMPLE)
    rent = round(r.p50 * 1.15 / 5) * 5
    return {**SAMPLE, "rent": rent}


@app.post("/estimate")
def estimate(listing: ListingIn) -> dict[str, Any]:
    m = get_model()
    feats = listing.features()
    r = m.estimate_range(feats)
    return {
        "currency": CURRENCY,
        "rent": listing.rent,
        "range": {"p10": r.p10, "p50": r.p50, "p90": r.p90},
        "verdict": verdict(listing.rent, r),
        "breakdown": m.explain(feats),
        "negotiation": negotiation_hint(listing.rent, r),
    }


@app.post("/alternatives")
def alternatives(listing: ListingIn) -> dict[str, Any]:
    m = get_model()
    found = find_alternatives(m.listings, listing.features(), listing.rent)
    return {"currency": CURRENCY, "alternatives": found}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
