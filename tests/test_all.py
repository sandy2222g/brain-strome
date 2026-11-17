from datetime import date

import pytest
from fastapi.testclient import TestClient

from streakkeep.api import app
from streakkeep.core import StreakError, heatmap, load, parse_days, runs, strict_summary, summary

RAW = load()
TODAY = date.fromisoformat(RAW["today"])
c = TestClient(app)


def test_runs_with_grace():
    days = parse_days(["2026-01-01", "2026-01-02", "2026-01-04", "2026-01-08"])
    assert [r[2] for r in runs(days, 1)] == [3, 1]
    assert [r[2] for r in runs(days, 0)] == [2, 1, 1]


def test_grace_keeps_streak_alive():
    s = summary(RAW["done"], TODAY, 1)
    assert s["alive"] and s["current"] > strict_summary(RAW["done"], TODAY)["current"]


def test_strict_current_by_hand():
    # check-ins run Nov 4..Nov 16 with no gap after the Nov 3 miss
    assert strict_summary(RAW["done"], TODAY)["current"] == 13


def test_longest_streak_found():
    s = summary(RAW["done"], TODAY, 1)
    assert s["longest"] >= s["current"]
    assert s["longest_span"][0] <= s["longest_span"][1]


def test_streak_dies_after_grace():
    s = summary(["2026-11-10"], TODAY, 1)
    assert s["current"] == 0 and not s["alive"]


def test_checkin_today_counts():
    s = summary(["2026-11-16", "2026-11-17"], TODAY, 0)
    assert s["current"] == 2


def test_duplicates_ignored():
    assert summary(["2026-11-16", "2026-11-16"], TODAY)["total_checkins"] == 1


def test_heatmap_shape():
    g = heatmap(RAW["done"], TODAY)
    assert len(g) == 9 and all(len(r) == 7 for r in g)
    assert g[-1][2] == "future" and g[-1][0] == "done" and g[-1][1] == "miss"


def test_validation():
    with pytest.raises(StreakError):
        summary([], TODAY)
    with pytest.raises(StreakError):
        summary(["2026-12-01"], TODAY)
    with pytest.raises(StreakError):
        parse_days(["nope"])
    with pytest.raises(StreakError):
        runs([], -1)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/streak", json={"done": RAW["done"], "today": RAW["today"], "grace_days": 1}).json()
    assert r["streak"]["current"] > r["strict"]["current"]
    assert c.get("/").status_code == 200
    assert c.post("/streak", json={"done": [], "today": "2026-11-17"}).status_code == 422
