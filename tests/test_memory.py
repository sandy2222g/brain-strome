from __future__ import annotations

import pytest

from runway.memory import initial_stability, next_review_in, retention, review


def test_retention_decays_and_bounds() -> None:
    assert retention(0, 3) == 1.0
    assert retention(3, 3) == pytest.approx(0.3679, abs=1e-3)
    assert retention(10, 3) < retention(5, 3) < 1.0
    assert retention(-2, 3) == 1.0


def test_retention_needs_positive_stability() -> None:
    with pytest.raises(ValueError):
        retention(1, 0)


def test_initial_stability_ordering_and_validation() -> None:
    assert initial_stability(0.9, 0.2) > initial_stability(0.1, 0.2)
    assert initial_stability(0.5, 0.9) < initial_stability(0.5, 0.1)
    with pytest.raises(ValueError):
        initial_stability(1.5, 0.5)


def test_review_always_grows_stability_more_when_forgotten() -> None:
    s = 2.0
    assert review(s, 0.95, 0.5) > s
    assert review(s, 0.3, 0.5) > review(s, 0.95, 0.5)
    assert review(s, 0.5, 0.9) < review(s, 0.5, 0.1)


def test_next_review_in() -> None:
    assert next_review_in(5.0, 0.8) == pytest.approx(1.116, abs=1e-3)
    with pytest.raises(ValueError):
        next_review_in(5.0, 1.0)
