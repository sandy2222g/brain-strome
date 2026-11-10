from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from sniffer.categorize import CategoryModel
from sniffer.detect import Txn

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def cats() -> CategoryModel:
    m = CategoryModel()
    m.fit(pd.read_csv(ROOT / "data" / "merchants.csv"))
    return m


def monthly(name: str, amount: float, start: date, n: int, step: int = 30) -> list[Txn]:
    return [Txn(start + timedelta(days=step * i), name, -amount) for i in range(n)]
