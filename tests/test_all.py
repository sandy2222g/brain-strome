import pytest
from fastapi.testclient import TestClient

from timetable.api import app
from timetable.core import (
    Section,
    TimetableError,
    best_timetable,
    build_courses,
    campus_days,
    clashes,
    credits_of,
    idle_minutes,
    load,
    register_in_order,
)

MAX, COURSES = load()
ORDER = register_in_order(MAX, COURSES)
BEST = best_timetable(MAX, COURSES)
c = TestClient(app)


def sec(code, *meetings):
    return Section(code, tuple(meetings))


def test_clash_detection_edges():
    a = sec("a", ("Mon", 540, 600))
    assert clashes(a, sec("b", ("Mon", 570, 630)))  # overlap
    assert not clashes(a, sec("c", ("Mon", 600, 660)))  # back to back is fine
    assert not clashes(a, sec("d", ("Tue", 540, 600)))  # other day


def test_days_and_idle_by_hand():
    chosen = [sec("a", ("Mon", 540, 600)), sec("b", ("Mon", 660, 720), ("Wed", 540, 600))]
    assert campus_days(chosen) == 2 and idle_minutes(chosen) == 60


def test_best_timetable_has_no_clashes():
    secs = list(BEST.values())
    assert all(not clashes(x, y) for i, x in enumerate(secs) for y in secs[i + 1 :])


def test_best_includes_every_required_course_and_respects_the_cap():
    assert all(course.name in BEST for course in COURSES if course.required)
    assert credits_of(COURSES, BEST) <= MAX


def test_best_beats_registering_in_order():
    assert credits_of(COURSES, BEST) > credits_of(COURSES, ORDER)
    assert campus_days(list(BEST.values())) < campus_days(list(ORDER.values()))
    assert any(course.required and course.name not in ORDER for course in COURSES)  # baseline drops a required one


def test_sample_numbers():
    assert (credits_of(COURSES, BEST), campus_days(list(BEST.values()))) == (15, 3)
    assert credits_of(COURSES, ORDER) == 14 and campus_days(list(ORDER.values())) == 5


def test_infeasible_required_courses_raise():
    raw = [
        {
            "name": "A",
            "credits": 3,
            "required": True,
            "sections": [{"code": "a", "meetings": [["Mon", "09:00", "10:00"]]}],
        },
        {
            "name": "B",
            "credits": 3,
            "required": True,
            "sections": [{"code": "b", "meetings": [["Mon", "09:30", "10:30"]]}],
        },
    ]
    with pytest.raises(TimetableError):
        best_timetable(10, build_courses(raw))  # the two required courses clash
    with pytest.raises(TimetableError):
        best_timetable(5, build_courses(raw))  # required credits exceed the cap


def test_validation():
    with pytest.raises(TimetableError):
        build_courses([])
    bad = [{"name": "A", "credits": 3, "sections": [{"code": "a", "meetings": [["Sun", "09:00", "10:00"]]}]}]
    with pytest.raises(TimetableError):
        build_courses(bad)
    bad = [{"name": "A", "credits": 3, "sections": [{"code": "a", "meetings": [["Mon", "11:00", "10:00"]]}]}]
    with pytest.raises(TimetableError):
        build_courses(bad)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/build", json={"max_credits": body["max_credits"], "courses": body["courses"]}).json()
    assert r["best"]["credits"] == 15 and r["best"]["days"] == 3 and r["best"]["missing_required"] == []
    assert r["in_order"]["missing_required"] == ["Databases"]
    assert c.get("/").status_code == 200


def test_api_validation():
    course = {
        "name": "A",
        "credits": 3,
        "required": True,
        "sections": [{"code": "a", "meetings": [["Mon", "09:00", "10:00"]]}],
    }
    assert c.post("/build", json={"max_credits": 2, "courses": [course]}).status_code == 422
