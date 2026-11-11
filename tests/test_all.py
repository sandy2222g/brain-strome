from itertools import combinations

import pytest
from fastapi.testclient import TestClient

from hallbook.api import app
from hallbook.core import (
    BookingError,
    Request,
    best_bookings,
    build,
    earliest_finish,
    first_come_first_served,
    load,
    overlaps,
    revenue,
)

REQS = load()
BEST = best_bookings(REQS)
c = TestClient(app)


def test_overlap_edges():
    a = Request("a", 540, 600, 1)
    assert overlaps(a, Request("b", 570, 630, 1))
    assert not overlaps(a, Request("c", 600, 660, 1))  # back to back is fine


def test_no_schedule_double_books_the_hall():
    for chosen in (BEST, first_come_first_served(REQS), earliest_finish(REQS)):
        assert all(not overlaps(x, y) for x, y in combinations(chosen, 2))


def test_dp_matches_brute_force_over_every_subset():
    best = 0.0
    for mask in range(1 << len(REQS)):
        pick = [r for k, r in enumerate(REQS) if mask >> k & 1]
        if all(not overlaps(x, y) for x, y in combinations(pick, 2)):
            best = max(best, revenue(pick))
    assert revenue(BEST) == best == 655


def test_sample_numbers():
    assert revenue(first_come_first_served(REQS)) == 480
    assert revenue(earliest_finish(REQS)) == 205
    assert [r.name for r in BEST] == ["Yoga class", "Wedding reception", "Charity quiz"]


def test_earliest_finish_maximises_count_not_fees():
    assert len(earliest_finish(REQS)) >= len(BEST) and revenue(earliest_finish(REQS)) < revenue(BEST)


def test_one_big_request_beats_many_small_ones():
    reqs = [Request("big", 0, 600, 100), Request("a", 0, 300, 30), Request("b", 300, 600, 30)]
    assert [r.name for r in best_bookings(reqs)] == ["big"]


def test_validation():
    ok = {"name": "a", "start": "09:00", "end": "10:00", "fee": 5}
    with pytest.raises(BookingError):
        build([])
    with pytest.raises(BookingError):
        build([{**ok, "start": "11:00"}])
    with pytest.raises(BookingError):
        build([ok, ok])
    with pytest.raises(BookingError):
        build([{**ok, "start": "9am"}])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/book", json=c.get("/sample").json()).json()
    assert (r["best"]["revenue"], r["first_come"]["revenue"], r["earliest_finish"]["revenue"]) == (655, 480, 205)
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/book", json={"requests": []}).status_code == 422
