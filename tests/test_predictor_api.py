from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from runway.api import app
from runway.predictor import ScoreModel


def test_score_model_beats_baseline(score_model: ScoreModel) -> None:
    assert score_model.metrics["test_mae"] < score_model.metrics["baseline_mae"] * 0.6


def test_score_model_monotonic_in_hours(score_model: ScoreModel) -> None:
    base = {"n_sessions": 20, "spacing_days": 2.0, "difficulty": 0.5, "prior_confidence": 0.3, "sleep_hours": 7}
    assert score_model.predict(total_hours=40, **base) > score_model.predict(total_hours=8, **base)


def test_score_model_cramming_is_worse(score_model: ScoreModel) -> None:
    base = {"total_hours": 30, "n_sessions": 20, "difficulty": 0.5, "prior_confidence": 0.3, "sleep_hours": 7}
    assert score_model.predict(spacing_days=2.5, **base) > score_model.predict(spacing_days=0.0, **base)


def test_api_flow() -> None:
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert "Exam Runway" in c.get("/").text
        assert "test_mae" in c.get("/metrics").json()
        sample = c.get("/sample").json()
        r = c.post("/plan", json=sample)
        assert r.status_code == 200
        body = r.json()
        assert 0 <= body["predicted_score"] <= 100 and 0 <= body["exam_readiness"] <= 1
        assert len(body["days"]) == 21 and set(body["readiness"]) == {t["name"] for t in sample["topics"]}


def test_api_validation() -> None:
    soon = (date.today() + timedelta(days=10)).isoformat()
    topic = {"name": "A", "weight": 1, "difficulty": 0.5, "confidence": 0.2}
    with TestClient(app) as c:
        assert c.post("/plan", json={"topics": [], "exam_date": soon}).status_code == 422
        past = (date.today() - timedelta(days=1)).isoformat()
        assert c.post("/plan", json={"topics": [topic], "exam_date": past}).status_code == 422
        bad = {"topics": [topic], "exam_date": soon, "rest_weekdays": [9]}
        assert c.post("/plan", json=bad).status_code == 422
        assert c.post("/plan", json={"topics": [{**topic, "difficulty": 2}], "exam_date": soon}).status_code == 422


def test_curve_endpoint() -> None:
    with TestClient(app) as c:
        pts = c.get("/curve", params={"stability": 4, "days": 10}).json()["points"]
        assert pts[0]["retention"] == 1.0 and pts[-1]["retention"] < pts[1]["retention"]
        assert c.get("/curve", params={"stability": 0}).status_code == 422
        assert pytest.approx(pts[4]["retention"], abs=1e-3) == 0.3679
