from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from triage.model import TriageModel, load_dataset  # noqa: E402


@pytest.fixture(scope="session")
def dataset():  # type: ignore[no-untyped-def]
    return load_dataset(ROOT / "data" / "tickets.csv")


@pytest.fixture(scope="session")
def model(dataset) -> TriageModel:  # type: ignore[no-untyped-def]
    m = TriageModel()
    m.fit(dataset)
    return m
