import math

import pytest
from fastapi.testclient import TestClient

from pacer.api import app
from pacer.core import (
    CourseError,
    Segment,
    budget_for_even_speed,
    build,
    effort,
    even_plan,
    load,
    optimal_plan,
    terrain_factor,
    total_hours,
)

SEGS, EVEN = load()
BUDGET = budget_for_even_speed(SEGS, EVEN)
OPT = optimal_plan(SEGS, BUDGET)
FLAT = even_plan(SEGS, BUDGET)
c = TestClient(app)


def test_terrain_factor_values():
    assert terrain_factor(0) == 1
    assert terrain_factor(5) == pytest.approx(1.4)
    assert terrain_factor(-5) == pytest.approx(0.85)
    assert terrain_factor(-30) == 0.5  # floor


def test_both_plans_spend_exactly_the_effort_budget():
    assert effort(SEGS, OPT) == pytest.approx(BUDGET)
    assert effort(SEGS, FLAT) == pytest.approx(BUDGET)


def test_even_plan_holds_the_stated_even_speed():
    assert FLAT[0] == pytest.approx(EVEN)


def test_optimal_plan_is_faster_than_even_pace_on_a_hilly_course():
    assert total_hours(SEGS, OPT) < total_hours(SEGS, FLAT)
    saved = (total_hours(SEGS, FLAT) - total_hours(SEGS, OPT)) * 3600
    assert 20 < saved < 60  # about half a minute on the sample course


def test_optimal_plan_runs_slower_uphill_and_faster_downhill():
    up = max(range(len(SEGS)), key=lambda i: SEGS[i].grade)
    down = min(range(len(SEGS)), key=lambda i: SEGS[i].grade)
    assert OPT[up] < EVEN < OPT[down]


def test_no_random_perturbation_beats_the_optimum_at_equal_effort():
    import random

    r = random.Random(1)
    best = total_hours(SEGS, OPT)
    for _ in range(300):
        v = [x * (1 + r.uniform(-0.15, 0.15)) for x in OPT]
        scale = math.sqrt(BUDGET / effort(SEGS, v))  # rescale to the same effort
        assert total_hours(SEGS, [x * scale for x in v]) >= best - 1e-12


def test_flat_course_has_no_gain():
    flat = [Segment(1.0, 0.0)] * 5
    budget = budget_for_even_speed(flat, 10)
    assert total_hours(flat, optimal_plan(flat, budget)) == pytest.approx(total_hours(flat, even_plan(flat, budget)))


def test_validation():
    with pytest.raises(CourseError):
        build([], 10)
    with pytest.raises(CourseError):
        build([Segment(1, 50)], 10)
    with pytest.raises(CourseError):
        build([Segment(0, 1)], 10)
    with pytest.raises(CourseError):
        build([Segment(1, 1)], 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json=c.get("/sample").json()).json()
    assert r["optimal"]["minutes"] < r["even"]["minutes"] and r["even"]["effort_used"] == pytest.approx(1)
    assert round(r["even"]["minutes"], 1) == 54.5 and 20 < r["seconds_saved"] < 60
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/plan", json={"segments": [], "even_kmh": 10}).status_code == 422
