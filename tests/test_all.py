import itertools

import pytest
from fastapi.testclient import TestClient

from playfit.api import app
from playfit.core import PlaylistError, Song, best_fit, build, in_order, load, total

RAW = load()
SONGS, TARGET = build(RAW["songs"], RAW["target_minutes"])
c = TestClient(app)


def brute(songs, target):
    best = 0
    for r in range(len(songs) + 1):
        for combo in itertools.combinations(songs, r):
            t = sum(s.seconds for s in combo)
            if t <= target:
                best = max(best, t)
    return best


def test_matches_brute_force_small():
    songs = [Song(str(i), s) for i, s in enumerate([200, 170, 310, 95, 240, 180, 130, 260, 115, 205])]
    for target in (300, 600, 777, 1500):
        assert total(best_fit(songs, target)) == brute(songs, target)


def test_never_exceeds_target():
    assert total(best_fit(SONGS, TARGET)) <= TARGET


def test_beats_or_ties_in_order():
    for minutes in (10, 30, 60, 90):
        assert total(best_fit(SONGS, minutes * 60)) >= total(in_order(SONGS, minutes * 60))


def test_sample_is_very_tight():
    assert TARGET - total(best_fit(SONGS, TARGET)) <= 5


def test_exact_fit_found():
    songs = [Song("a", 100), Song("b", 200), Song("c", 300)]
    assert [s.title for s in best_fit(songs, 500)] == ["b", "c"]


def test_prefers_fewer_songs_for_same_total():
    songs = [Song("a", 100), Song("b", 100), Song("c", 200)]
    assert [s.title for s in best_fit(songs, 200)] == ["c"]


def test_keeps_original_order():
    idx = [SONGS.index(s) for s in best_fit(SONGS, TARGET)]
    assert idx == sorted(idx)


def test_in_order_stops_at_first_overrun():
    songs = [Song("a", 100), Song("b", 500), Song("c", 50)]
    assert [s.title for s in in_order(songs, 200)] == ["a"]


def test_validation():
    with pytest.raises(PlaylistError):
        build([], 10)
    with pytest.raises(PlaylistError):
        build([{"title": "x", "seconds": 5}], 10)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/fit", json=c.get("/sample").json()).json()
    assert r["best"]["seconds"] <= r["target"] and r["best"]["seconds"] >= r["in_order"]["seconds"]
    assert c.get("/").status_code == 200
    assert c.post("/fit", json={"target_minutes": 0, "songs": []}).status_code == 422
