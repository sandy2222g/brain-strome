
import pytest
from fastapi.testclient import TestClient

from plankcut.api import app
from plankcut.core import PlankError, best_cuts, build, load, single_size

RAW = load()
PRICES = build(RAW["prices"], RAW["length"])
c = TestClient(app)


def brute(prices, length):
    best = 0.0
    sizes = list(prices)

    def go(rest, start, val):
        nonlocal best
        best = max(best, val)
        for i in range(start, len(sizes)):
            if sizes[i] <= rest:
                go(rest - sizes[i], i, val + prices[sizes[i]])

    go(length, 0, 0.0)
    return round(best, 2)


def test_matches_brute_force():
    for length in (30, 70, 100, 170, 240, 300):
        assert best_cuts(PRICES, length)[0] == brute(PRICES, length)


def test_pieces_fit_and_sum_to_value():
    value, pieces = best_cuts(PRICES, 240)
    assert sum(pieces) <= 240 and value == round(sum(PRICES[p] for p in pieces), 2)


def test_beats_single_size_baseline():
    assert best_cuts(PRICES, 240)[0] > single_size(PRICES, 240)[0]


def test_never_worse_than_baseline():
    for length in range(30, 400, 17):
        assert best_cuts(PRICES, length)[0] >= single_size(PRICES, length)[0]


def test_too_short_plank_gives_nothing():
    assert best_cuts(PRICES, 20) == (0.0, [])


def test_exact_single_piece():
    assert best_cuts({50: 7.5}, 50) == (7.5, [50])


def test_pieces_sorted_longest_first():
    pieces = best_cuts(PRICES, 240)[1]
    assert pieces == sorted(pieces, reverse=True)


def test_validation():
    with pytest.raises(PlankError):
        build({}, 100)
    with pytest.raises(PlankError):
        build({"0": 1.0}, 100)
    with pytest.raises(PlankError):
        build({"30": 4.0}, 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/cut", json=c.get("/sample").json()).json()
    assert r["best"]["value"] > r["single_size"]["value"] and r["best"]["waste"] >= 0
    assert c.get("/").status_code == 200
    assert c.post("/cut", json={"length": 0, "prices": {}}).status_code == 422
