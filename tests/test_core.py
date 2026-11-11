from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from conftest import DAY, team
from meetfair.core import (
    SLEEP_MIN,
    MeetingError,
    Person,
    best_slots,
    candidate_slots,
    hour_cost,
    rotation,
    score_slot,
    slot_pain,
    validate,
)


def test_hour_cost_shape() -> None:
    p = Person("A", "UTC")
    assert hour_cost(p, 10) == 0 and hour_cost(p, 17.0) == 0
    assert hour_cost(p, 7) == 4.0 and hour_cost(p, 19) == 4.0  # two hours outside work, squared
    assert hour_cost(p, 3) >= SLEEP_MIN and hour_cost(p, 23) >= SLEEP_MIN


def test_deeper_sleep_costs_more() -> None:
    p = Person("A", "UTC")
    assert hour_cost(p, 3.0) > hour_cost(p, 22.5) and hour_cost(p, 3.0) > hour_cost(p, 6.0)


def test_same_zone_team_meets_in_working_hours() -> None:
    top = best_slots(team("Europe/Berlin", "Europe/Berlin"), DAY, 60)[0]
    assert top.total_pain == 0 and top.sleepers == 0


def test_neighbouring_zones_find_zero_pain_slot() -> None:
    assert best_slots(team("Europe/London", "Europe/Berlin", "Europe/Athens"), DAY, 60)[0].worst_pain == 0


def test_opposite_sides_of_the_world_have_no_perfect_slot_and_are_flagged() -> None:
    top = best_slots(team("Pacific/Auckland", "America/New_York", "Europe/London"), DAY, 60)[0]
    assert top.worst_pain > 0


def test_longer_meetings_never_hurt_less() -> None:
    people = team("Asia/Kolkata", "America/New_York")
    short = best_slots(people, DAY, 30)[0].score
    long = best_slots(people, DAY, 120)[0].score
    assert long >= short


def test_slot_pain_uses_the_worst_hour_in_the_meeting() -> None:
    p = Person("A", "UTC")
    start = datetime(2026, 11, 16, 16, 30, tzinfo=UTC)
    assert slot_pain(p, start, 30) == 0
    assert slot_pain(p, start, 90) > 0  # runs to 18:00


def test_dst_shifts_local_time() -> None:
    p = Person("A", "America/New_York")
    summer = score_slot([p, Person("B", "UTC")], datetime(2026, 7, 15, 14, 0, tzinfo=UTC), 60).people[0].local_start
    winter = score_slot([p, Person("B", "UTC")], datetime(2026, 12, 15, 14, 0, tzinfo=UTC), 60).people[0].local_start
    assert (summer, winter) == ("10:00", "09:00")


def test_ranking_is_deterministic_and_sorted() -> None:
    a = candidate_slots(team("Asia/Tokyo", "Europe/Berlin"), DAY)
    b = candidate_slots(team("Asia/Tokyo", "Europe/Berlin"), DAY)
    assert [s.start_utc for s in a] == [s.start_utc for s in b]
    assert [s.score for s in a] == sorted(s.score for s in a)
    assert len(a) == 48


def test_fairness_weight_penalises_the_worst_off() -> None:
    people = team("Asia/Kolkata", "America/New_York", "Europe/Berlin")
    total_only = best_slots(people, DAY, 60, 1, lam=0.0)[0]
    fair = best_slots(people, DAY, 60, 1, lam=3.0)[0]
    assert fair.worst_pain <= total_only.worst_pain


def test_rotation_shares_pain_better_than_one_fixed_slot() -> None:
    people = team(
        "Asia/Kolkata", "America/Sao_Paulo", "Europe/Berlin", "Australia/Sydney", "Africa/Accra", "America/New_York"
    )
    r = rotation(people, DAY, 8)
    assert r.max_pain_rotation < r.max_pain_fixed and r.spread < r.fixed_spread
    assert len(r.weeks) == 8 and len({s.start_utc.hour for s in r.weeks}) > 1


def test_rotation_never_worse_than_fixed_when_one_slot_is_perfect() -> None:
    r = rotation(team("Europe/London", "Europe/Berlin"), DAY, 6)
    assert r.max_pain_rotation == 0 == r.max_pain_fixed


@pytest.mark.parametrize(
    ("people", "duration"),
    [
        ([Person("A", "UTC")], 60),
        ([Person("A", "UTC"), Person("A", "UTC")], 60),
        ([Person("A", "UTC"), Person("B", "Mars/Olympus")], 60),
        ([Person("A", "UTC"), Person("B", "UTC")], 20),
        ([Person("A", "UTC", 18, 9), Person("B", "UTC")], 60),
    ],
)
def test_validation(people: list[Person], duration: int) -> None:
    with pytest.raises(MeetingError):
        validate(people, duration)


def test_rotation_week_bounds() -> None:
    with pytest.raises(MeetingError):
        rotation(team("UTC", "Europe/Berlin"), date(2026, 11, 16), 1)
