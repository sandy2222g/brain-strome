import pytest
from fastapi.testclient import TestClient

from dinnersync.api import app
from dinnersync.core import (
    MealError,
    Step,
    finish_times,
    load,
    peak_usage,
    sequential_schedule,
    span,
    sync_schedule,
    validate,
    waiting_minutes,
)

CAP, DISHES = load()
SYNC = sync_schedule(CAP, DISHES)
SEQ = sequential_schedule(CAP, DISHES)
c = TestClient(app)


def steps_of(dish):
    return [s for s in SYNC if s.dish == dish]


def test_every_step_is_scheduled_with_its_full_duration():
    expected = {(s.dish, s.step): s.minutes for d in DISHES for s in d}
    got = {(s.dish, s.step): s.start - s.end for s in SYNC}
    assert got == expected


def test_steps_within_a_dish_keep_their_order():
    for d in DISHES:
        slots = sorted(steps_of(d[0].dish), key=lambda s: -s.start)
        assert [s.step for s in slots] == [s.step for s in d]
        for earlier, later in zip(slots, slots[1:], strict=False):
            assert earlier.end >= later.start  # the next step never starts before the previous one ends


def test_resource_capacity_is_never_exceeded_in_either_schedule():
    for slots in (SYNC, SEQ):
        for r, cap in CAP.items():
            assert peak_usage(slots, r) <= cap


def test_synced_plan_is_shorter_and_keeps_food_hotter_than_the_sequential_one():
    assert span(SYNC) < span(SEQ)
    assert waiting_minutes(SYNC) < waiting_minutes(SEQ) / 2


def test_main_dishes_finish_exactly_at_serving_time():
    ft = finish_times(SYNC)
    assert ft["Roast chicken"] == 0 and ft["Roast potatoes"] == 0 and ft["Green beans"] == 0


def test_a_single_dish_has_no_waiting():
    one = [[Step("Soup", "Chop", 10, "hands"), Step("Soup", "Simmer", 20, "hob")]]
    plan = sync_schedule({"hands": 1, "hob": 1}, one)
    assert waiting_minutes(plan) == 0 and span(plan) == 30


def test_more_oven_capacity_never_lengthens_the_plan():
    more = {**CAP, "oven": 2}
    assert span(sync_schedule(more, DISHES)) <= span(SYNC)
    assert waiting_minutes(sync_schedule(more, DISHES)) <= waiting_minutes(SYNC)


def test_validation():
    with pytest.raises(MealError):
        validate(CAP, [])
    with pytest.raises(MealError):
        validate({"hands": 1}, [[Step("x", "y", 5, "oven")]])
    with pytest.raises(MealError):
        validate(CAP, [[Step("x", "y", 0, "hands")]])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/plan", json={"capacity": body["capacity"], "dishes": body["dishes"]}).json()
    assert r["synced"]["span"] < r["sequential"]["span"] and r["peak"]["oven"] == 1
    assert c.get("/").status_code == 200


def test_api_validation():
    bad = {
        "capacity": {"hands": 1},
        "dishes": [{"name": "x", "steps": [{"step": "y", "minutes": 5, "resource": "oven"}]}],
    }
    assert c.post("/plan", json=bad).status_code == 422
    assert c.post("/plan", json={"capacity": {}, "dishes": []}).status_code == 422
