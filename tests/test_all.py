import itertools

import pytest
from fastapi.testclient import TestClient

from hwplan.api import app
from hwplan.core import PlanError, in_order, load, moore_hodgson, shortest_first

T = load()["tasks"]
c = TestClient(app)


def brute_best(tasks):
    best = 0
    for perm in itertools.permutations(tasks):
        t, n = 0.0, 0
        for x in perm:
            t += x["hours"]
            n += t <= x["due"]
        best = max(best, n)
    return best


def test_sample_matches_brute_force():
    assert moore_hodgson(T)["on_time_count"] == brute_best(T) == 6


def test_random_small_cases_match_brute_force():
    import random

    rng = random.Random(4)
    for _ in range(60):
        tasks = [
            {"name": f"t{i}", "hours": rng.randint(1, 6), "due": rng.randint(2, 20)} for i in range(rng.randint(1, 6))
        ]
        assert moore_hodgson(tasks)["on_time_count"] == brute_best(tasks)


def test_baselines_are_worse():
    assert in_order(T)["on_time_count"] == 2
    assert shortest_first(T)["on_time_count"] == 5


def test_late_task_is_the_lab_report_and_goes_last():
    s = moore_hodgson(T)["schedule"]
    assert s[-1]["name"] == "Lab report" and not s[-1]["on_time"]
    assert all(r["on_time"] for r in s[:-1])


def test_total_hours_is_sum():
    assert moore_hodgson(T)["total_hours"] == sum(t["hours"] for t in T)


def test_everything_fits_when_loose():
    loose = [{"name": "a", "hours": 1, "due": 10}, {"name": "b", "hours": 2, "due": 10}]
    assert moore_hodgson(loose)["on_time_count"] == 2


def test_validation():
    with pytest.raises(PlanError):
        moore_hodgson([])
    with pytest.raises(PlanError):
        moore_hodgson([{"name": "x", "hours": 0, "due": 5}])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json={"tasks": T}).json()
    assert r["plan"]["on_time_count"] == 6 and r["listed_on_time"] == 2 and r["shortest_on_time"] == 5
    assert c.get("/").status_code == 200
    assert c.post("/plan", json={"tasks": []}).status_code == 422
