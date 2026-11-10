"""Day-by-day study plan builder.

Greedy simulation: each study day, topics are ranked by how much a session is worth now
(forgotten fraction x exam weight x difficulty bonus); sessions are placed until the day's
hour budget is used. Each session updates the topic's memory stability, so intervals expand.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

from runway.memory import initial_stability, retention, review

MIN_SESSION_H = 0.5
FINAL_REVIEW_DAYS = 3


@dataclass(frozen=True)
class Topic:
    name: str
    weight: float  # share of marks, any positive number
    difficulty: float  # 0 easy .. 1 hard
    confidence: float  # 0 know nothing .. 1 mastered


@dataclass
class Session:
    topic: str
    hours: float
    retention_before: float


@dataclass
class Day:
    date: date
    sessions: list[Session] = field(default_factory=list)

    @property
    def hours(self) -> float:
        return round(sum(s.hours for s in self.sessions), 2)


@dataclass
class Plan:
    days: list[Day]
    readiness: dict[str, float]  # retention at the exam, per topic
    half_life_days: dict[str, float]  # days after the exam until recall falls to 50%
    exam_readiness: float  # weight-averaged retention at the exam
    warnings: list[str]
    total_hours: float


def session_hours(difficulty: float) -> float:
    """Harder topics get longer sessions (0.5h to 1.5h, in 0.25h steps)."""
    return round((MIN_SESSION_H + difficulty) * 4) / 4


def build_plan(
    topics: list[Topic],
    exam_date: date,
    start: date,
    hours_per_day: float,
    rest_weekdays: tuple[int, ...] = (),
) -> Plan:
    if not topics:
        raise ValueError("at least one topic is required")
    if exam_date <= start:
        raise ValueError("exam date must be after the start date")
    if hours_per_day < MIN_SESSION_H:
        raise ValueError(f"hours_per_day must be at least {MIN_SESSION_H}")
    if any(t.weight <= 0 for t in topics):
        raise ValueError("topic weights must be positive")

    stability = {t.name: initial_stability(t.confidence, t.difficulty) for t in topics}
    last_seen = {t.name: start for t in topics}
    by_name = {t.name: t for t in topics}
    total_weight = sum(t.weight for t in topics)

    days: list[Day] = []
    day = start
    while day < exam_date:
        entry = Day(date=day)
        days.append(entry)
        if day.weekday() in rest_weekdays:
            day += timedelta(days=1)
            continue
        budget = hours_per_day
        scores: list[tuple[float, str]] = []
        for t in topics:
            r_now = retention((day - last_seen[t.name]).days, stability[t.name])
            # Value of studying now: how much is forgotten, scaled by importance and difficulty.
            # Closer to the exam, forgotten material is worth proportionally more.
            urgency = 1.0 + 1.5 / max((exam_date - day).days, 1)
            scores.append(((1.0 - r_now) * (t.weight / total_weight) * (0.6 + t.difficulty) * urgency, t.name))
        scores.sort(key=lambda s: (-s[0], s[1]))
        for _, name in scores:
            t = by_name[name]
            hours = min(session_hours(t.difficulty), budget)
            if hours < MIN_SESSION_H:
                continue
            r_now = retention((day - last_seen[name]).days, stability[name])
            days_left = (exam_date - day).days
            if r_now > 0.9 and days_left > FINAL_REVIEW_DAYS and (day - start).days > 0:
                continue  # skip: nothing to gain yet (but always allow a final review near the exam)
            entry.sessions.append(Session(topic=name, hours=hours, retention_before=round(r_now, 3)))
            stability[name] = review(stability[name], r_now, t.difficulty)
            last_seen[name] = day
            budget -= hours
        day += timedelta(days=1)

    readiness = {
        t.name: round(retention((exam_date - last_seen[t.name]).days, stability[t.name]), 3) for t in topics
    }
    exam_readiness = round(sum(readiness[t.name] * t.weight for t in topics) / total_weight, 3)
    total_hours = round(sum(d.hours for d in days), 2)
    half_life = {n: round(stability[n] * math.log(2), 1) for n in stability}
    warnings = _warnings(topics, readiness, days, hours_per_day)
    return Plan(days, readiness, half_life, exam_readiness, warnings, total_hours)


def _warnings(topics: list[Topic], readiness: dict[str, float], days: list[Day], hours_per_day: float) -> list[str]:
    out: list[str] = []
    for t in topics:
        if readiness[t.name] < 0.5:
            out.append(f"'{t.name}' is predicted at {readiness[t.name]:.0%} on exam day; add time or start earlier.")
    study_days = [d for d in days if d.sessions]
    if len(study_days) < 3:
        out.append("Fewer than 3 study days available: spaced repetition needs time between reviews.")
    if study_days and sum(d.hours for d in study_days) / len(study_days) < 0.6 * hours_per_day:
        out.append("The plan uses well under your daily budget; you could study fewer days or add harder topics.")
    return out
