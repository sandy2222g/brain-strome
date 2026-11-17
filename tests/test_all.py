import math

import pytest
from fastapi.testclient import TestClient

from sortrace.api import app
from sortrace.core import ALGOS, KINDS, SortError, Tracker, make_input, merge, run, table, thin

c = TestClient(app)


def test_every_algorithm_sorts_every_kind_of_input():
    for kind in KINDS:
        for n in (2, 3, 17, 100):
            data = make_input(kind, n)
            for a in ALGOS:
                assert run(a, data, keep_frames=False).a == sorted(data), (a, kind, n)


def test_edge_cases():
    for a in ALGOS:
        assert run(a, [1, 1, 1, 1], keep_frames=False).a == [1, 1, 1, 1]
        assert run(a, [], keep_frames=False).a == [] and run(a, [5], keep_frames=False).a == [5]


def test_exact_counts_on_known_inputs():
    n = 100
    assert run("insertion", make_input("sorted", n), False).comparisons == n - 1
    assert run("bubble", make_input("sorted", n), False).comparisons == n - 1  # early exit after one clean pass
    assert run("bubble", make_input("reversed", n), False).comparisons == n * (n - 1) // 2
    assert run("insertion", make_input("reversed", n), False).comparisons == n * (n - 1) // 2
    assert run("quick", make_input("sorted", n), False).comparisons == n * (n - 1) // 2  # worst case on purpose


def test_n_log_n_algorithms_stay_under_their_bound():
    n = 500
    bound = n * math.log2(n)
    for kind in KINDS:
        assert run("merge", make_input(kind, n), False).comparisons <= bound
        assert run("heap", make_input(kind, n), False).comparisons <= 2 * bound


def test_the_expected_winners_and_losers():
    t = table(200)
    assert t["random"]["merge"] < t["random"]["insertion"] < t["random"]["bubble"]
    assert t["sorted"]["insertion"] == t["sorted"]["bubble"] == 199 < t["sorted"]["merge"]
    assert t["sorted"]["quick"] > 5 * t["sorted"]["heap"]  # naive pivot meets sorted data
    assert t["nearly-sorted"]["insertion"] < t["nearly-sorted"]["bubble"] / 5


def test_merge_sort_is_stable():
    pairs = [(2, "a"), (1, "b"), (2, "c"), (1, "d")]

    class Key(int):
        pass

    t = Tracker([0] * 0)
    items = [Key(p[0]) for p in pairs]
    tags = {id(x): p[1] for x, p in zip(items, pairs, strict=True)}
    t.a = items  # type: ignore[assignment]
    merge(t)
    assert [tags[id(x)] for x in t.a] == ["b", "d", "a", "c"]


def test_frames_start_unsorted_and_end_sorted():
    t = run("insertion", make_input("random", 20))
    assert t.frames[0][1] != sorted(t.frames[0][1]) and t.frames[-1][1] == sorted(t.a)
    counts = [f[0] for f in t.frames]
    assert counts == sorted(counts)
    assert len(thin(t.frames, 10)) == 10 and thin(t.frames, 10)[-1] == t.frames[-1]


def test_validation():
    for k, n in [("nope", 10), ("random", 1), ("random", 5000)]:
        with pytest.raises(SortError):
            make_input(k, n)
    with pytest.raises(SortError):
        run("nope", [1, 2])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/race", params={"kind": "reversed", "n": 20}).json()
    assert set(r["lanes"]) == set(ALGOS) and r["lanes"]["bubble"]["comparisons"] == 190
    assert r["lanes"]["merge"]["frames"][-1][1] == sorted(r["input"]) and len(r["lanes"]["bubble"]["frames"]) <= 120
    assert c.get("/race", params={"n": 99}).status_code == 422
    assert c.get("/race", params={"kind": "x"}).status_code == 422
    assert c.get("/options").json()["table"]["random"]["merge"] < 1500 and c.get("/").status_code == 200
