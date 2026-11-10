from __future__ import annotations

import json
from pathlib import Path

import pytest

from seating.model import Guest, Problem

ROOT = Path(__file__).resolve().parents[1]


def to_problem(d: dict) -> Problem:  # type: ignore[type-arg]
    return Problem(
        guests=[Guest(g["name"], g["group"]) for g in d["guests"]],
        likes=[tuple(x) for x in d["likes"]],  # type: ignore[misc]
        dislikes=[tuple(x) for x in d["dislikes"]],  # type: ignore[misc]
        together=d["together"],
        apart=[tuple(x) for x in d["apart"]],  # type: ignore[misc]
        table_size=d["table_size"],
    )


@pytest.fixture(scope="session")
def party() -> dict:  # type: ignore[type-arg]
    return json.loads((ROOT / "data" / "sample_party.json").read_text())


@pytest.fixture(scope="session")
def problem(party: dict) -> Problem:  # type: ignore[type-arg]
    return to_problem(party)
