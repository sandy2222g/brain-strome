"""Plan race pacing over a hilly course with a fixed effort budget.

Model (an assumption): running at speed v over d km on a slope costs d * a * v^2 effort, where the terrain factor
a is 1 + 8 * grade for uphill (grade as a fraction), and 1 + 3 * grade for downhill, never below 0.5. The runner
has a fixed total effort budget E. Minimising total time sum(d / v) under sum(d * a * v^2) = E has a closed form
(Lagrange multipliers): v_i = k * a_i^(-1/3) with k = sqrt(E / sum(d_i * a_i^(1/3))). Running at one even speed
is the baseline: v = sqrt(E / sum(d_i * a_i)).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "course.json"
MAX_SEGMENTS = 200


class CourseError(ValueError):
    """Invalid course."""


@dataclass(frozen=True)
class Segment:
    km: float
    grade: float  # percent


def build(segments: list[Segment], even_kmh: float) -> tuple[list[Segment], float]:
    if not 1 <= len(segments) <= MAX_SEGMENTS:
        raise CourseError(f"between 1 and {MAX_SEGMENTS} segments")
    if even_kmh <= 0:
        raise CourseError("even pace must be positive")
    for s in segments:
        if s.km <= 0 or not -30 <= s.grade <= 30:
            raise CourseError("segments need positive length and a grade between -30 and 30 percent")
    return segments, even_kmh


def load(path: Path = DATA) -> tuple[list[Segment], float]:
    raw = json.loads(path.read_text())
    return build([Segment(s["km"], s["grade"]) for s in raw["segments"]], raw["even_kmh"])


def terrain_factor(grade_percent: float) -> float:
    g = grade_percent / 100
    return 1 + 8 * g if g >= 0 else max(0.5, 1 + 3 * g)


def effort(segments: list[Segment], speeds: list[float]) -> float:
    return sum(s.km * terrain_factor(s.grade) * v * v for s, v in zip(segments, speeds, strict=True))


def total_hours(segments: list[Segment], speeds: list[float]) -> float:
    return sum(s.km / v for s, v in zip(segments, speeds, strict=True))


def even_plan(segments: list[Segment], budget: float) -> list[float]:
    cost = sum(s.km * terrain_factor(s.grade) for s in segments)
    return [math.sqrt(budget / cost)] * len(segments)


def optimal_plan(segments: list[Segment], budget: float) -> list[float]:
    a = [terrain_factor(s.grade) for s in segments]
    k = math.sqrt(budget / sum(s.km * x ** (1 / 3) for s, x in zip(segments, a, strict=True)))
    return [k * x ** (-1 / 3) for x in a]


def budget_for_even_speed(segments: list[Segment], even_kmh: float) -> float:
    """Effort budget of a runner who could hold `even_kmh` on the whole course at even pace."""
    return even_kmh**2 * sum(s.km * terrain_factor(s.grade) for s in segments)
