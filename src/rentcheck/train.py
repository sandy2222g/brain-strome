"""Train the model from data/listings.csv and save it (run at Docker build time)."""

from __future__ import annotations

import json

from rentcheck.config import DATA_PATH, MODEL_PATH
from rentcheck.data import generate, load_listings
from rentcheck.model import RentModel


def train() -> RentModel:
    df = load_listings(DATA_PATH) if DATA_PATH.exists() else generate()
    model = RentModel().fit(df)
    model.save(MODEL_PATH)
    return model


if __name__ == "__main__":
    m = train()
    print(json.dumps(m.metrics, indent=2))
