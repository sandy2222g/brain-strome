from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import make_problem, person
from roster import rules
from roster.model import OFF, compile_problem

M, A, E, N = 0, 1, 2, 3  # template order: morning, afternoon, evening, night


def inst_for(*staff: dict, days: int = 7, **kw):
    return compile_problem(make_problem(list(staff), days=days, **kw))


def row(inst, assigned: dict[int, int]) -> list[int]:
    r = [OFF] * inst.D
    for d, k in assigned.items():
        r[d] = k
    return r


def names(inst, r) -> set[str]:
    return {v.rule for v in rules.row_violations(inst, 0, r)}


def test_leave_is_a_hard_rule():
    inst = inst_for(person("a", leave=[2]))
    assert rules.RULE_LEAVE in names(inst, row(inst, {2: M}))
    assert names(inst, row(inst, {3: M})) == set()


def test_evening_then_morning_breaks_eleven_hour_rest():
    inst = inst_for(person("a"))
    assert rules.RULE_REST in names(inst, row(inst, {0: E, 1: M}))
    assert names(inst, row(inst, {0: E, 1: A})) == set()  # 23:00 -> 12:00 is 13h


def test_night_then_day_shift_breaks_rest_but_night_after_night_is_fine():
    inst = inst_for(person("a"))
    assert rules.RULE_REST in names(inst, row(inst, {0: N, 1: A}))
    assert names(inst, row(inst, {0: N, 1: N})) == set()


def test_afternoon_then_morning_has_exactly_eleven_hours():
    inst = inst_for(person("a"))
    assert names(inst, row(inst, {0: A, 1: M})) == set()
    tighter = inst_for(person("a"), rules={"min_rest_hours": 12})
    assert rules.RULE_REST in names(tighter, row(tighter, {0: A, 1: M}))


def test_max_consecutive_days_uses_the_stricter_of_person_and_rule():
    inst = inst_for(person("a", max_consecutive_days=3))
    assert rules.RULE_CONSEC in names(inst, row(inst, {0: M, 1: M, 2: M, 3: M}))
    assert names(inst, row(inst, {0: M, 1: M, 2: M, 4: M, 5: M})) == set()
    capped = inst_for(person("a", max_consecutive_days=9), rules={"max_consecutive_days": 2})
    assert rules.RULE_CONSEC in names(capped, row(capped, {0: M, 1: M, 2: M}))


def test_weekly_hours_cap():
    inst = inst_for(person("a"), rules={"max_weekly_hours": 32})
    assert rules.RULE_WEEKLY in names(inst, row(inst, {0: M, 2: M, 3: M, 4: M, 6: M}))
    assert names(inst, row(inst, {0: M, 2: M, 3: M, 4: M})) == set()


def test_double_shift_is_reported_by_the_full_check():
    inst = inst_for(person("a"))
    grid = [row(inst, {0: M})]
    found = rules.violations(inst, grid, doubles=[(0, 0)])
    assert any(v.rule == rules.RULE_DOUBLE for v in found)


def test_headcount_cap_is_enforced_on_full_roster():
    inst = inst_for(*(person(x) for x in "abcd"))
    grid = [row(inst, {0: N}) for _ in range(4)]  # four people on a one-person night
    assert any(v.rule == rules.RULE_CAPACITY for v in rules.violations(inst, grid))


def test_block_reason_names_the_first_problem():
    inst = inst_for(person("a", leave=[1]), person("b"))
    grid = [row(inst, {}), row(inst, {0: E})]
    assert rules.block_reason(inst, grid, 0, 1, M) == rules.RULE_LEAVE
    assert rules.block_reason(inst, grid, 1, 1, M) == rules.RULE_REST
    assert rules.block_reason(inst, grid, 1, 0, M) == rules.RULE_DOUBLE
    assert rules.block_reason(inst, grid, 0, 3, M) is None


def test_problem_validation_rejects_bad_input():
    with pytest.raises(ValidationError):
        make_problem([person("a"), person("a")])
    with pytest.raises(ValidationError):
        make_problem([person("a", leave=[9])])
    with pytest.raises(ValidationError):
        make_problem(
            [person("a")],
            overrides=[{"day": 1, "kind": "night", "headcount": 1}],
            templates=[{"kind": "morning", "start_hour": 7, "hours": 8, "headcount": 1}],
        )
