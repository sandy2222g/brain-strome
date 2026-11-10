from __future__ import annotations

import pytest

from roster.generator import TEMPLATES, generate
from roster.model import Instance, Problem, compile_problem


def make_problem(staff: list[dict], days: int = 7, templates: list[dict] | None = None, **kw) -> Problem:
    return Problem.model_validate(
        {"name": "t", "days": days, "staff": staff, "templates": templates or TEMPLATES, **kw}
    )


def person(pid: str, skills: list[str] | None = None, hours: int = 40, **kw) -> dict:
    return {"id": pid, "name": pid.title(), "skills": skills or [], "contract_hours": hours, **kw}


@pytest.fixture(scope="session")
def week() -> Instance:
    return compile_problem(generate(2024, 1))


@pytest.fixture(scope="session")
def month() -> Instance:
    return compile_problem(generate(2024, 4))
