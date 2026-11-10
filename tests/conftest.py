from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from plantparent.model import IntervalModel

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def species() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "species.csv")


@pytest.fixture(scope="session")
def model() -> IntervalModel:
    m = IntervalModel()
    m.fit(pd.read_csv(ROOT / "data" / "observations.csv"))
    return m
