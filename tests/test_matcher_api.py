from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from lostfound.api import app
from lostfound.matcher import Matcher


def test_metrics_beat_text_only_baseline(matcher: Matcher) -> None:
    m = matcher.metrics
    assert m["recall_at_1"] >= 0.88 and m["recall_at_3"] >= 0.95
    assert m["recall_at_1"] > m["baseline_text_only_recall_at_1"]
    assert m["no_match_rejected"] >= 0.7
    assert m["feature_weights"]["category_conflict"] < 0 < m["feature_weights"]["same_color"]


def test_match_finds_the_planted_item(matcher: Matcher, found: pd.DataFrame, lost: pd.DataFrame) -> None:
    hits = 0
    sample = lost[lost["match_id"].notna()].head(30)
    for r in sample.to_dict("records"):
        top = matcher.match(r, found, k=1)[0]
        hits += int(top.found_id == r["match_id"])
    assert hits / len(sample) >= 0.85


def test_candidates_sorted_with_reasons(matcher: Matcher, found: pd.DataFrame) -> None:
    cands = matcher.match({"description": "Lost my red wallet", "place": "library", "date": "2026-10-01"}, found, k=5)
    assert len(cands) == 5 and [c.score for c in cands] == sorted((c.score for c in cands), reverse=True)
    assert all(0 <= c.score <= 1 for c in cands)


def test_empty_pool(matcher: Matcher, found: pd.DataFrame) -> None:
    assert matcher.match({"description": "lost phone", "place": "gym", "date": "2026-10-01"}, found.iloc[0:0]) == []


def test_save_load(matcher: Matcher, found: pd.DataFrame, tmp_path: Path) -> None:
    p = tmp_path / "m.joblib"
    matcher.save(p)
    row = {"description": "Lost my black phone", "place": "gym", "date": "2026-10-01"}
    assert Matcher.load(p).match(row, found, 1)[0].found_id == matcher.match(row, found, 1)[0].found_id


def test_api_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Lost and Found Desk" in c.get("/").text
        assert "recall_at_1" in c.get("/metrics").json()
        assert "library" in c.get("/places").json()
        listing = c.get("/found", params={"limit": 5}).json()
        assert listing["total"] >= 300 and len(listing["items"]) == 5
        sample = c.get("/sample-lost").json()
        assert len(sample) == 4
        r = c.post("/match", json=sample[0])
        assert r.status_code == 200 and len(r.json()["candidates"]) == 5


def test_hand_in_then_match_finds_it() -> None:
    with TestClient(app) as c:
        item = {
            "description": "Found a Zenmark yellow umbrella with a name tag",
            "place": "library",
            "date": "2026-10-20",
        }
        new_id = c.post("/found", json=item).json()["id"]
        res = c.post(
            "/match", json={"description": "Lost my Zenmark yellow umbrella", "place": "library", "date": "2026-10-19"}
        )
        assert res.json()["candidates"][0]["found_id"] == new_id and res.json()["confident"]


def test_api_validation() -> None:
    with TestClient(app) as c:
        assert c.post("/match", json={"description": "x", "date": "2026-10-01"}).status_code == 422
        assert c.post("/match", json={"description": "lost phone", "date": "not-a-date"}).status_code == 422
        assert c.post("/found", json={"description": "", "date": "2026-10-01"}).status_code == 422
