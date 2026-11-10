from __future__ import annotations

from datetime import date

import pytest

from conftest import EXAM, START, TOPICS
from runway.planner import Topic, build_plan, session_hours


def test_session_hours_scale_with_difficulty() -> None:
    assert session_hours(0.0) == 0.5
    assert session_hours(1.0) == 1.5
    assert session_hours(0.9) > session_hours(0.1)


def test_plan_respects_budget_window_and_rest_days() -> None:
    plan = build_plan(TOPICS, EXAM, START, 3.0, rest_weekdays=(6,))
    assert plan.days[0].date == START and plan.days[-1].date == date(2026, 3, 22)
    assert all(d.date < EXAM for d in plan.days)
    assert all(d.hours <= 3.0 + 1e-9 for d in plan.days)
    assert all(not d.sessions for d in plan.days if d.date.weekday() == 6)


def test_plan_is_deterministic() -> None:
    a = build_plan(TOPICS, EXAM, START, 3.0)
    b = build_plan(TOPICS, EXAM, START, 3.0)
    assert [(d.date, [(s.topic, s.hours) for s in d.sessions]) for d in a.days] == [
        (d.date, [(s.topic, s.hours) for s in d.sessions]) for d in b.days
    ]


def test_hard_heavy_topic_gets_most_hours() -> None:
    plan = build_plan(TOPICS, EXAM, START, 3.0)
    hours = {t.name: 0.0 for t in TOPICS}
    for d in plan.days:
        for s in d.sessions:
            hours[s.topic] += s.hours
    assert hours["Hard"] > hours["Easy"]


def test_intervals_expand() -> None:
    plan = build_plan([Topic("Only", 1, 0.5, 0.2)], EXAM, START, 2.0)
    study_dates = [d.date for d in plan.days if d.sessions]
    gaps = [(b - a).days for a, b in zip(study_dates, study_dates[1:], strict=False)]
    assert len(gaps) >= 3 and gaps[-1] >= gaps[0]


def test_more_time_means_better_readiness() -> None:
    low = build_plan(TOPICS, EXAM, START, 1.0)
    high = build_plan(TOPICS, EXAM, START, 4.0)
    assert high.exam_readiness >= low.exam_readiness
    assert high.total_hours > low.total_hours


def test_warnings_when_too_little_time() -> None:
    plan = build_plan(TOPICS, date(2026, 3, 5), START, 0.5)
    assert plan.warnings


@pytest.mark.parametrize(
    ("kwargs", "msg"),
    [
        ({"exam": START}, "after the start"),
        ({"hours": 0.1}, "at least"),
        ({"topics": []}, "at least one topic"),
        ({"topics": [Topic("x", 0, 0.5, 0.5)]}, "positive"),
    ],
)
def test_validation(kwargs: dict, msg: str) -> None:
    with pytest.raises(ValueError, match=msg):
        build_plan(kwargs.get("topics", TOPICS), kwargs.get("exam", EXAM), START, kwargs.get("hours", 3.0))


def test_spaced_plan_builds_longer_half_life_than_cramming() -> None:
    spaced = build_plan(TOPICS, EXAM, START, 3.0)
    crammed = build_plan(TOPICS, EXAM, date(2026, 3, 21), 3.0)
    assert sum(spaced.half_life_days.values()) > sum(crammed.half_life_days.values())
