import itertools

import pytest
from fastapi.testclient import TestClient

from morningplan.api import app
from morningplan.core import RoutineError, fmt, load, parse, schedule, tails, wake_time

D = load()
T = D["tasks"]
c = TestClient(app)


def test_time_helpers():
    assert parse("08:15") == 495 and fmt(-30) == "23:30"


def test_sample_makespan_and_wake():
    r = wake_time(D["leave"], T)
    assert r["total"] == 44 and r["wake"] == "07:31"
    assert r["one_at_a_time"] == 53 and r["wake_one_at_a_time"] == "07:22"


def test_makespan_equals_active_work_here():
    active = sum(t["min"] for t in T if not t.get("hands_free"))
    assert schedule(T)["total"] == active == 44  # nothing can beat the hands-on minutes


def test_lower_bound_is_the_dependency_chain():
    assert schedule(T)["lower_bound"] == 25  # kettle, coffee, breakfast, teeth, coat


def test_dependencies_respected_and_one_person():
    rows = {r["name"]: r for r in schedule(T)["rows"]}
    for t in T:
        for dep in t["after"]:
            assert rows[t["name"]]["start"] >= rows[dep]["end"]
    hands = sorted((r["start"], r["end"]) for r in rows.values() if not r["hands_free"])
    assert all(a[1] <= b[0] for a, b in zip(hands, hands[1:], strict=False))


def test_hands_free_overlap_with_work():
    rows = {r["name"]: r for r in schedule(T)["rows"]}
    assert rows["Boil kettle"]["start"] == 0 and rows["Shower"]["start"] == 0


def brute(tasks):
    by = {t["name"]: t for t in tasks}
    act = [t["name"] for t in tasks if not t.get("hands_free")]
    best = None
    for order in itertools.permutations(act):
        end, free = {}, 0
        pending = list(order)
        ok = True
        for n in order:
            t = by[n]
            deps = t["after"]
            for d in deps:
                if by[d].get("hands_free") and d not in end:
                    s = max((end[x] for x in by[d]["after"]), default=0)
                    end[d] = s + by[d]["min"]
            if any(d not in end for d in deps):
                ok = False
                break
            s = max([free] + [end[d] for d in deps])
            end[n] = free = s + t["min"]
            pending.remove(n)
        if ok:
            best = free if best is None else min(best, free)
    return best


def test_never_better_than_brute_force_and_equal_on_sample():
    sample_brute = brute(T)
    assert sample_brute is not None and schedule(T)["total"] >= sample_brute
    assert schedule(T)["total"] == sample_brute


def test_cycle_detected():
    loop = [{"name": "a", "min": 1, "after": ["b"]}, {"name": "b", "min": 1, "after": ["a"]}]
    with pytest.raises(RoutineError):
        schedule(loop)
    assert tails({"a": {"min": 1, "after": []}}) == {"a": 1}


def test_validation():
    with pytest.raises(RoutineError):
        schedule([])
    with pytest.raises(RoutineError):
        schedule([{"name": "a", "min": 1, "after": ["zzz"]}])
    with pytest.raises(RoutineError):
        schedule([{"name": "a", "min": 0, "after": []}])
    with pytest.raises(RoutineError):
        parse("25:00")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/plan", json={"leave": D["leave"], "tasks": T}).json()
    assert r["wake"] == "07:31" and r["total"] == 44
    assert c.get("/").status_code == 200
    assert c.post("/plan", json={"leave": "x", "tasks": T}).status_code == 422
