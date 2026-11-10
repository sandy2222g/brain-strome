"""Paths, feature lists and the made-up city definition."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "listings.csv"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / "rentcheck.joblib"
STATIC_DIR = ROOT / "static"

CURRENCY = "€"
SEED = 42
N_LISTINGS = 4000
QUANTILES = (0.1, 0.5, 0.9)
TARGET_COVERAGE = 0.8

# name -> (base rent per m2, typical km to centre, typical km to metro)
DISTRICTS: dict[str, tuple[float, float, float]] = {
    "Old Harbour": (21.0, 1.2, 0.4),
    "Market Square": (23.5, 0.6, 0.3),
    "Linden Park": (18.5, 2.8, 0.7),
    "Foundry Row": (15.5, 3.6, 0.9),
    "Riverside": (17.0, 3.1, 0.8),
    "Kestrel Hill": (14.0, 5.2, 1.3),
    "Mill Lane": (12.5, 6.4, 1.6),
    "Northgate": (11.5, 7.8, 2.0),
}

NUMERIC = [
    "bedrooms",
    "bathrooms",
    "size_m2",
    "floor",
    "furnished",
    "balcony",
    "lift",
    "building_age",
    "dist_centre_km",
    "dist_metro_km",
    "pets_allowed",
]
CATEGORICAL = ["district"]
FEATURES = ["district", *NUMERIC]
TARGET = "rent"

# Plain-language names for the price breakdown.
LABELS = {
    "bedrooms": "Number of bedrooms",
    "bathrooms": "Number of bathrooms",
    "size_m2": "Floor area",
    "floor": "Floor level",
    "furnished": "Furnished",
    "balcony": "Balcony",
    "lift": "Lift in building",
    "building_age": "Building age",
    "dist_centre_km": "Distance to centre",
    "dist_metro_km": "Distance to metro",
    "pets_allowed": "Pets allowed",
}
