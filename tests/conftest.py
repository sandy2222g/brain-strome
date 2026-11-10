from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from lostfound.matcher import Matcher

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def found() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "found.csv")


@pytest.fixture(scope="session")
def lost() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "lost.csv")


@pytest.fixture(scope="session")
def matcher(found: pd.DataFrame, lost: pd.DataFrame) -> Matcher:
    m = Matcher()
    m.fit(found, lost)
    return m
