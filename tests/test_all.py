import pytest
from fastapi.testclient import TestClient

from liftweek.api import app
from liftweek.core import DAYS, PlanError, load, pick_days, plan

ex = load()
c = TestClient(app)
ALL = list(ex)


def test_pick_days_even_spread():
    assert pick_days(3) == [0, 2, 4]
    assert pick_days(4) == [0, 1, 3, 5] and pick_days(2) == [0, 3]
    assert pick_days(7) == list(range(7)) and pick_days(1) == [0]


def test_pick_days_bounds():
    for bad in (0, 8):
        with pytest.raises(PlanError):
            pick_days(bad)


def test_every_exercise_placed_or_reported():
    r = plan(ALL, 4, 60)
    placed = [n for v in r["week"].values() for n in v]
    assert sorted(placed + r["unplaced"]) == sorted(ALL)


def test_time_budget_respected():
    r = plan(ALL, 4, 45)
    assert all(m <= 45 for m in r["minutes"].values())


def test_tight_budget_reports_unplaced():
    r = plan(ALL, 2, 20)
    assert r["unplaced"]


def test_no_consecutive_clash_when_possible():
    r = plan(["Bench press", "Squat", "Barbell row", "Overhead press"], 4, 60)
    assert r["recovery_clashes"] == 0


def test_same_muscle_grouped_into_one_day():
    r = plan(["Biceps curl", "Pull-up", "Barbell row", "Squat"], 3, 60)
    days = [d for d, v in r["week"].items() if "Pull-up" in v or "Barbell row" in v]
    assert len(days) == 1


def test_single_day_has_no_clashes():
    assert plan(ALL, 1, 180)["recovery_clashes"] == 0


def test_unknown_and_empty():
    with pytest.raises(PlanError):
        plan(["Moonwalk"], 3, 45)
    with pytest.raises(PlanError):
        plan([], 3, 45)


def test_days_labels_valid():
    assert set(plan(ALL, 5, 90)["week"]) <= set(DAYS)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/exercises").json()) == len(ALL)
    r = c.post("/plan", json={"exercises": ALL, "days": 4, "minutes_per_day": 60}).json()
    assert len(r["week"]) == 4
    assert c.get("/").status_code == 200


def test_api_errors():
    assert c.post("/plan", json={"exercises": ["x"], "days": 3}).status_code == 422
    assert c.post("/plan", json={"exercises": ALL, "days": 9}).status_code == 422
