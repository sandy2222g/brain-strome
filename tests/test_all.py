import pytest
from fastapi.testclient import TestClient

from energywatch.api import app
from energywatch.core import (
    Reading,
    UsageError,
    alerts,
    evaluate,
    fit,
    load,
    naive_alerts,
    score,
)

ROWS = load()
TRAIN = [r for r in ROWS if r.day < 14]
TEST = [r for r in ROWS if r.day >= 14]
MODEL = fit(TRAIN)
c = TestClient(app)


def test_data_shape_and_labels():
    assert len(ROWS) == 28 * 24 and sum(1 for r in ROWS if r.fault) == 8 + 6 + 5 + 4
    assert all(not r.fault for r in TRAIN)


def test_model_has_a_baseline_for_every_slot():
    assert len(MODEL) == 48 and all(spread > 0 for _, spread in MODEL.values())


def test_fault_hours_score_far_higher_than_normal_hours_on_median():
    normal = sorted(abs(score(MODEL, r)) for r in TEST if not r.fault)
    faulty = sorted(abs(score(MODEL, r)) for r in TEST if r.fault)
    assert normal[len(normal) // 2] < 1.5 and faulty[len(faulty) // 2] > 5
    assert normal[-1] > faulty[0]  # single hours overlap: the run rule, not the score alone, avoids false alarms


def test_all_faults_caught_with_no_false_alarms_at_default():
    e = evaluate(TEST, alerts(MODEL, TEST, 4.0, 2))
    assert e["faults"] == 4 and e["faults_caught"] == 4 and e["false_alarms"] == 0


def test_min_run_removes_single_hour_false_alarms():
    single = evaluate(TEST, alerts(MODEL, TEST, 3.0, 1))
    runs = evaluate(TEST, alerts(MODEL, TEST, 3.0, 2))
    assert single["false_alarms"] > runs["false_alarms"] and runs["faults_caught"] == single["faults_caught"]


def test_seasonal_baseline_beats_flat_three_sigma_rule():
    ours = evaluate(TEST, alerts(MODEL, TEST))
    naive = evaluate(TEST, naive_alerts(TRAIN, TEST))
    assert ours["faults_caught"] > naive["faults_caught"] and ours["false_alarms"] <= naive["false_alarms"]


def test_outage_is_flagged_low_and_heater_high():
    by_day = {a.day: a.direction for a in alerts(MODEL, TEST)}
    assert by_day[27] == "low" and by_day[22] == "high"


def test_alert_requires_consecutive_same_sign_hours():
    base = [r for r in TEST if r.day == 14]
    spiky = [Reading(r.day, r.hour, r.weekday, r.kwh + (3.0 if r.hour in (3, 9) else 0), "") for r in base]
    assert alerts(MODEL, spiky, 4.0, 2) == []
    assert len(alerts(MODEL, spiky, 4.0, 1)) == 2


def test_missing_slot_and_empty_training_raise():
    with pytest.raises(UsageError):
        fit([])
    with pytest.raises(UsageError):
        score({}, TEST[0])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/analyse").json()
    assert len(r["cells"]) == 14 * 24 and r["eval"]["faults_caught"] == 4 and r["naive_eval"]["faults_caught"] < 4
    assert c.get("/").status_code == 200


def test_api_params_and_validation():
    loose = c.get("/analyse", params={"threshold": 2.0, "min_run": 1}).json()
    strict = c.get("/analyse", params={"threshold": 9.0, "min_run": 3}).json()
    assert len(loose["alerts"]) >= len(strict["alerts"])
    assert c.get("/analyse", params={"threshold": 0.1}).status_code == 422
