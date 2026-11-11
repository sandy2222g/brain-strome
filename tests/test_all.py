import itertools
import random

import pytest
from fastapi.testclient import TestClient

from timebox.api import app
from timebox.core import (
    Event,
    PlanError,
    Task,
    best_plan,
    free_gaps,
    hhmm,
    in_order_plan,
    load,
    place,
    total_priority,
    validate,
)

DAY = load()
GAPS = free_gaps(DAY["day_start"], DAY["day_end"], DAY["events"])
TASKS = DAY["tasks"]
c = TestClient(app)


def test_free_gaps_subtract_events_and_merge_overlaps():
    g = free_gaps(9, 17, [Event("a", 10, 11), Event("b", 10.5, 12)])
    assert g == [(9, 10), (12, 17)]


def test_free_gaps_edge_cases():
    assert free_gaps(9, 12, []) == [(9, 12)]
    assert free_gaps(9, 12, [Event("all", 8, 13)]) == []
    with pytest.raises(PlanError):
        free_gaps(12, 9, [])
    with pytest.raises(PlanError):
        free_gaps(9, 12, [Event("bad", 11, 10)])


def test_place_respects_gaps_deadlines_and_no_overlap():
    plan = place(TASKS[-3:], GAPS, 5)
    assert plan is not None
    for a, b in itertools.combinations(sorted(plan, key=lambda p: p.start), 2):
        assert a.end <= b.start + 1e-9
    for p in plan:
        assert any(g0 - 1e-9 <= p.start and p.end <= g1 + 1e-9 for g0, g1 in GAPS)


def test_place_fails_when_deadline_is_impossible():
    assert place([Task("x", 120, 5, 9.5)], [(9.0, 12.0)], 0) is None


def test_best_plan_is_feasible_and_meets_deadlines():
    plan = best_plan(TASKS, GAPS, 5)
    by_title = {t.title: t for t in TASKS}
    for p in plan:
        dl = by_title[p.title].deadline
        assert dl is None or p.end <= dl + 1e-9
    assert len({p.title for p in plan}) == len(plan)


def test_best_plan_never_worse_than_in_order_and_strictly_better_on_sample():
    best, naive = total_priority(best_plan(TASKS, GAPS, 5)), total_priority(in_order_plan(TASKS, GAPS, 5))
    assert best >= naive
    assert best > naive


def test_best_plan_is_optimal_over_all_subsets_on_random_days():
    rng = random.Random(3)
    for _ in range(15):
        tasks = [
            Task(f"t{i}", rng.choice([20, 30, 45, 60]), rng.randint(1, 5), rng.choice([None, 11.0, 13.0]))
            for i in range(6)
        ]
        gaps = [(9.0, 10.5), (11.0, 13.5)]
        best = total_priority(best_plan(tasks, gaps, 5))
        brute = max(
            sum(t.priority for t in combo)
            for r in range(7)
            for combo in itertools.combinations(tasks, r)
            if place(list(combo), gaps, 5) is not None
        )
        assert best == brute


def test_more_free_time_never_lowers_value():
    small = total_priority(best_plan(TASKS, [(9.0, 12.0)], 5))
    big = total_priority(best_plan(TASKS, [(9.0, 12.0), (13.0, 17.0)], 5))
    assert big >= small


def test_validation():
    with pytest.raises(PlanError):
        validate([Task("x", 0, 3)])
    with pytest.raises(PlanError):
        validate([Task("x", 10, 9)])
    with pytest.raises(PlanError):
        validate([Task(f"t{i}", 10, 1) for i in range(15)])
    assert hhmm(9.5) == "09:30"


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert r["priority"] > r["in_order_priority"] and r["plan"] and r["free_hours"] > 4
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/plan", json={"tasks": []}).status_code == 422
    bad = {
        "day_start": 9,
        "day_end": 18,
        "events": [{"title": "x", "start": 11, "end": 10}],
        "tasks": [{"title": "a", "minutes": 10, "priority": 3}],
    }
    assert c.post("/plan", json=bad).status_code == 422
