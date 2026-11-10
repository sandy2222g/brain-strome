from __future__ import annotations

import pytest

from carbon.calculator import calculate
from carbon.levers import BY_ID, LEVERS, rank_levers, saving_kg
from carbon.plan import MAX_PLAN, PlanError, build_plan, suggest_plan
from conftest import make_answers


def test_lever_savings_never_exceed_affected_categories() -> None:
    for answers in (make_answers(), make_answers(heating="oil", diet="meat_heavy", flights_long=3)):
        fp = calculate(answers)
        for lever in LEVERS:
            saved = saving_kg(lever, answers)
            if saved is None:
                continue
            affected = sum(fp.by_category_kg[c] for c in lever.affects)
            assert 0 <= saved <= affected + 1e-6, lever.id


def test_levers_ranked_by_impact_per_effort() -> None:
    ranked = rank_levers(make_answers())
    scores = [r.impact_per_effort for r in ranked]
    assert scores == sorted(scores, reverse=True)
    assert all(1 <= r.effort <= 5 and r.saved_t > 0 for r in ranked)


def test_lever_values_by_hand() -> None:
    a = make_answers()
    assert saving_kg(BY_ID["thermostat_down"], a) == pytest.approx(2070 - 9000 * 0.93 * 0.23)
    assert saving_kg(BY_ID["green_tariff"], a) == pytest.approx(300 * 12 * 0.17)
    assert saving_kg(BY_ID["flight_cut"], a) == pytest.approx(1500)
    assert saving_kg(BY_ID["car_to_bus"], a) == pytest.approx(20 * 52 * (0.17 - 0.07))


def test_levers_that_do_not_apply_are_left_out() -> None:
    a = make_answers(diet="vegan", car_type="ev", heating="heat_pump", flights_short=0, flights_long=0)
    ids = {r.id for r in rank_levers(a)}
    assert not ids & {"meat_free_2", "electric_car", "heat_pump", "flight_cut"}
    assert saving_kg(BY_ID["flight_cut"], a) is None


def test_plan_does_not_double_count_overlapping_levers() -> None:
    a = make_answers(car_km_week=300)
    plan = build_plan(a, ["car_to_bus", "electric_car"])
    alone = sum(s.alone_t for s in plan.steps)
    assert plan.saved_t < alone  # shifting km and then electrifying the rest overlap
    changed = BY_ID["electric_car"].apply(BY_ID["car_to_bus"].apply(a))  # type: ignore[arg-type]
    assert plan.saved_t == pytest.approx((calculate(a).total_kg - calculate(changed).total_kg) / 1000, abs=1e-3)  # type: ignore[arg-type]
    assert plan.interaction_t < 0


def test_plan_steps_add_up_to_total() -> None:
    plan = build_plan(make_answers(), ["heat_pump", "green_tariff", "flight_cut"])
    assert sum(s.in_plan_t for s in plan.steps) == pytest.approx(plan.saved_t, abs=2e-3)
    assert plan.baseline_t - plan.after_t == pytest.approx(plan.saved_t, abs=2e-3)
    assert sum(plan.after_by_category_kg.values()) / 1000 == pytest.approx(plan.after_t, abs=2e-3)


def test_heat_pump_and_green_tariff_work_together() -> None:
    plan = build_plan(make_answers(), ["heat_pump", "green_tariff"])
    assert plan.interaction_t > 0  # green power also cleans the heat pump's electricity


def test_single_lever_plan_equals_lever_saving() -> None:
    a = make_answers()
    plan = build_plan(a, ["meat_free_2"])
    assert plan.saved_t == pytest.approx(saving_kg(BY_ID["meat_free_2"], a) / 1000, abs=1e-3)  # type: ignore[operator]


def test_plan_validation() -> None:
    a = make_answers()
    with pytest.raises(PlanError, match="unknown"):
        build_plan(a, ["teleport"])
    with pytest.raises(PlanError, match="at most"):
        build_plan(a, ["thermostat_down", "green_tariff", "flight_cut", "heat_pump"])
    with pytest.raises(PlanError, match="does not apply"):
        build_plan(make_answers(diet="vegan"), ["meat_free_2"])


def test_duplicate_levers_count_once() -> None:
    a = make_answers()
    assert build_plan(a, ["flight_cut", "flight_cut"]).saved_t == build_plan(a, ["flight_cut"]).saved_t


def test_suggested_plan_is_valid_and_distinct() -> None:
    a = make_answers()
    ids = suggest_plan(a)
    assert 1 <= len(ids) <= MAX_PLAN and len(set(ids)) == len(ids)
    assert build_plan(a, ids).saved_t > 0
