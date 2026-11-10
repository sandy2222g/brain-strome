from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from pantry.recipes import RecipeRanker, load_recipes  # noqa: E402
from pantry.waste_model import WasteModel  # noqa: E402

TODAY = date(2026, 1, 12)


@pytest.fixture(scope="session")
def model() -> WasteModel:
    return WasteModel().fit(pd.read_csv(ROOT / "data" / "waste_events.csv"))


@pytest.fixture(scope="session")
def ranker() -> RecipeRanker:
    return RecipeRanker(load_recipes(ROOT / "data" / "recipes.csv"))
