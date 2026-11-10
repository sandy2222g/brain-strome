"""Train the waste-risk model from data/waste_events.csv (generated if absent) and persist it."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from pantry.waste_model import WasteModel, generate_waste_events

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "waste_events.csv"
MODEL_PATH = Path(os.environ.get("MODEL_PATH", ROOT / "models" / "waste.joblib"))


def train(save_path: Path | None = None) -> WasteModel:
    df = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else generate_waste_events()
    model = WasteModel().fit(df)
    model.save(save_path or MODEL_PATH)
    return model


if __name__ == "__main__":
    m = train()
    print(json.dumps(m.metrics, indent=2))
    print(f"saved -> {MODEL_PATH}")
