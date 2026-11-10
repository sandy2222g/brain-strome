from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import RISKY, SAFE
from noshow.model import NoShowModel, age_group, fairness_audit, load_dataset, risk_band


def test_risk_band_thresholds() -> None:
    assert risk_band(0.9)[0] == "high"
    assert risk_band(0.4)[0] == "medium"
    assert risk_band(0.05)[0] == "low"
    assert risk_band(0.55)[0] == "high"


def test_age_group() -> None:
    assert [age_group(a) for a in (10, 25, 60, 61)] == ["<25", "25-60", "25-60", ">60"]


def test_load_dataset_missing_columns(tmp_path: Path) -> None:
    p = tmp_path / "x.csv"
    p.write_text("age,no_show\n3,0\n")
    with pytest.raises(ValueError, match="missing columns"):
        load_dataset(p)


def test_metrics_beat_baseline(model: NoShowModel) -> None:
    m = model.metrics
    assert m["test_auc"] > 0.7
    assert m["test_brier"] < m["baseline_brier"]
    assert m["selected_model"] in m["cv_auc"]


def test_risky_scores_higher_than_safe(model: NoShowModel) -> None:
    assert model.predict(RISKY).probability > model.predict(SAFE).probability + 0.2
    assert model.predict(RISKY).band in {"medium", "high"}
    assert model.predict(SAFE).band == "low"


def test_probabilities_are_calibrated_in_aggregate(model: NoShowModel, dataset: pd.DataFrame) -> None:
    probs = model.predict_proba(dataset.drop(columns=["no_show"]).to_dict("records"))
    assert abs(probs.mean() - dataset["no_show"].mean()) < 0.03


def test_plan_day_ranks_and_sums(model: NoShowModel) -> None:
    plan = model.plan_day([SAFE, RISKY, SAFE])
    assert plan["items"][0]["probability"] >= plan["items"][-1]["probability"]
    assert plan["appointments"] == 3
    assert plan["expected_no_shows"] == pytest.approx(sum(i["probability"] for i in plan["items"]), abs=0.05)
    assert plan["suggested_overbook"] <= plan["expected_no_shows"]


def test_fairness_audit_structure(model: NoShowModel) -> None:
    audit = model.metrics["fairness"]
    assert set(audit) == {"age_group", "insurance"}
    assert set(audit["insurance"]) == {"public", "private", "none"}
    assert all(0 <= g["flag_rate"] <= 1 for grp in audit.values() for g in grp.values())


def test_fairness_audit_single_class_group() -> None:
    df = pd.DataFrame({"age": [30, 30], "insurance": ["public", "public"], "no_show": [0, 0]})
    res = fairness_audit(df, np.array([0.1, 0.2]))
    assert res["insurance"]["public"]["auc"] is None


def test_save_load_roundtrip(model: NoShowModel, tmp_path: Path) -> None:
    path = tmp_path / "m.joblib"
    model.save(path)
    loaded = NoShowModel.load(path)
    assert loaded.predict(RISKY).probability == pytest.approx(model.predict(RISKY).probability)
