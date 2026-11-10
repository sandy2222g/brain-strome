from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from runway.planner import Topic
from runway.predictor import ScoreModel, load_dataset

ROOT = Path(__file__).resolve().parents[1]
START = date(2026, 3, 2)  # a Monday
EXAM = date(2026, 3, 23)

TOPICS = [
    Topic("Hard", weight=3, difficulty=0.9, confidence=0.1),
    Topic("Medium", weight=2, difficulty=0.5, confidence=0.4),
    Topic("Easy", weight=1, difficulty=0.1, confidence=0.7),
]


@pytest.fixture(scope="session")
def score_model() -> ScoreModel:
    m = ScoreModel()
    m.fit(load_dataset(ROOT / "data" / "study_sessions.csv"))
    return m
