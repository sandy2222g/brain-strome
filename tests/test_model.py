from __future__ import annotations

from pathlib import Path

import pytest

from triage.model import PRIORITY_ORDER, SLA_HOURS, TriageModel, build_text, load_dataset


def test_build_text_upweights_subject() -> None:
    assert build_text("Hello", "World") == "Hello Hello World"


def test_dataset_is_balanced_and_valid(dataset) -> None:  # type: ignore[no-untyped-def]
    assert len(dataset) >= 1000
    assert set(dataset["priority"]) <= set(PRIORITY_ORDER)
    assert dataset["category"].nunique() == 5


def test_load_dataset_rejects_unknown_priority(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("subject,body,category,priority\na,b,billing,CRITICAL\n")
    with pytest.raises(ValueError, match="unknown priority"):
        load_dataset(p)


def test_metrics_meet_floor(model: TriageModel) -> None:
    assert model.metrics["category_accuracy"] >= 0.9
    assert model.metrics["priority_accuracy"] >= 0.6


@pytest.mark.parametrize(
    ("subject", "body", "category"),
    [
        ("charged twice", "I was charged twice and want a refund of my invoice", "billing"),
        ("app crashes", "The application crashes with error 500 when I save", "technical"),
        ("password", "I forgot my password and I am locked out of my account", "account"),
        ("package", "My parcel was never delivered and tracking has not updated", "shipping"),
        ("dark mode", "It would be great if you could add a dark mode feature", "feature_request"),
    ],
)
def test_category_predictions(model: TriageModel, subject: str, body: str, category: str) -> None:
    assert model.predict(subject, body).category == category


def test_priority_signals(model: TriageModel) -> None:
    urgent = model.predict("down", "Our service crashes. Production is down, this is urgent, need help immediately")
    low = model.predict("idea", "Please add dark mode. No rush, just a small suggestion whenever you have time")
    assert PRIORITY_ORDER.index(urgent.priority) > PRIORITY_ORDER.index(low.priority)
    assert urgent.sla_hours == SLA_HOURS[urgent.priority]


def test_prediction_shape_and_explanation(model: TriageModel) -> None:
    p = model.predict("refund", "refund my payment charge please")
    assert 0.0 < p.category_confidence <= 1.0
    assert p.top_terms and all(isinstance(t, str) for t in p.top_terms)


def test_empty_vocabulary_text_gives_no_terms(model: TriageModel) -> None:
    assert model.predict("", "zzqx").top_terms == []


def test_batch_matches_single(model: TriageModel) -> None:
    items = [("a", "charged twice refund"), ("b", "app crashes error 500")]
    batch = model.predict_batch(items)
    assert [b.category for b in batch] == [model.predict(*i).category for i in items]


def test_save_load_roundtrip(model: TriageModel, tmp_path: Path) -> None:
    path = tmp_path / "m.joblib"
    model.save(path)
    loaded = TriageModel.load(path)
    assert loaded.predict("x", "charged twice refund").category == model.predict("x", "charged twice refund").category
    assert path.with_suffix(".metrics.json").exists()
