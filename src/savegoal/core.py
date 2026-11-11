"""Savings goal maths: months to reach a goal, and the monthly deposit needed to hit it by a date.

Deposits are made at the end of each month; interest is the annual rate / 12, credited monthly.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "goal.json"
MAX_MONTHS = 1200


class GoalError(ValueError):
    """Invalid goal inputs."""


def check(goal: float, start: float, monthly: float, annual_rate: float) -> None:
    if goal <= 0 or start < 0 or monthly < 0 or not 0 <= annual_rate <= 0.3:
        raise GoalError("goal > 0, start >= 0, monthly >= 0 and a rate between 0 and 0.3")


def balance_curve(start: float, monthly: float, annual_rate: float, months: int) -> list[float]:
    """Balance after each month, index 0 = today."""
    r = annual_rate / 12
    out = [start]
    for _ in range(months):
        out.append(out[-1] * (1 + r) + monthly)
    return out


def months_to_goal(goal: float, start: float, monthly: float, annual_rate: float) -> int | None:
    """First month the balance reaches the goal, or None within 100 years."""
    check(goal, start, monthly, annual_rate)
    bal, r = start, annual_rate / 12
    for m in range(MAX_MONTHS + 1):
        if bal >= goal - 1e-9:
            return m
        bal = bal * (1 + r) + monthly
    return None


def months_without_interest(goal: float, start: float, monthly: float) -> int | None:
    if start >= goal:
        return 0
    return math.ceil((goal - start) / monthly) if monthly > 0 else None


def required_monthly(goal: float, start: float, months: int, annual_rate: float) -> float:
    """Closed-form deposit that lands exactly on the goal after `months` months."""
    check(goal, start, 0, annual_rate)
    if not 1 <= months <= MAX_MONTHS:
        raise GoalError(f"months must be 1-{MAX_MONTHS}")
    r = annual_rate / 12
    grown = start * (1 + r) ** months
    if r == 0:
        return max(0.0, (goal - start) / months)
    return max(0.0, (goal - grown) * r / ((1 + r) ** months - 1))


def load(path: Path = DATA) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text())
