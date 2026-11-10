from __future__ import annotations

import json
from pathlib import Path

import pytest

from buddies.model import Student

ROOT = Path(__file__).resolve().parents[1]


def mk(
    name: str,
    skills: dict[str, int] | None = None,
    slots: tuple[str, ...] = (),
    style: str = "quiet",
    goal: str = "exam",
) -> Student:
    return Student(name, skills or {}, slots, style, goal)


@pytest.fixture(scope="session")
def cohort() -> list[Student]:
    d = json.loads((ROOT / "data" / "students.json").read_text())
    return [Student(s["name"], s["skills"], tuple(s["slots"]), s["style"], s["goal"]) for s in d["students"]]
