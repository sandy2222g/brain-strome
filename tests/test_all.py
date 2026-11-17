import pytest
from fastapi.testclient import TestClient

from abjudge.api import app
from abjudge.core import ABError, analyse, false_positive_rate, sample_size

c = TestClient(app)


def test_textbook_example():
    # 200/2000 vs 250/2000, by hand: pooled p = 0.1125, se = sqrt(0.1125 * 0.8875 * 2/2000) = 0.00999,
    # so z = 0.025 / 0.00999 = 2.50
    r = analyse(200, 2000, 250, 2000)
    assert r["z"] == pytest.approx(2.50, abs=0.01) and r["p_value"] == pytest.approx(0.0124, abs=0.0005)
    assert r["significant"] and r["ci_low"] > 0


def test_identical_groups_are_not_significant():
    r = analyse(100, 1000, 100, 1000)
    assert r["z"] == 0 and r["p_value"] == 1.0 and not r["significant"]
    assert r["ci_low"] < 0 < r["ci_high"]


def test_symmetry_swapping_groups_flips_sign_not_p():
    a, b = analyse(120, 1000, 150, 1000), analyse(150, 1000, 120, 1000)
    assert a["p_value"] == b["p_value"] and a["z"] == -b["z"]


def test_sample_size_matches_published_figure():
    # 10% baseline, detect +2 points at 80% power, 5% alpha: about 3,800 per group (standard calculators)
    assert 3700 <= sample_size(0.10, 0.02) <= 3900
    assert sample_size(0.10, 0.01) > 3 * sample_size(0.10, 0.02)  # half the lift needs about 4x the traffic


def test_peeking_inflates_false_positives():
    one, many = false_positive_rate(1, trials=800), false_positive_rate(10, trials=800)
    assert one == pytest.approx(0.05, abs=0.02)  # an honest single look
    assert many > 2.5 * one  # repeated peeking makes "winners" out of noise


def test_validation():
    for bad in [(5, 0, 1, 10), (11, 10, 1, 10)]:
        with pytest.raises(ABError):
            analyse(*bad)
    with pytest.raises(ABError):
        sample_size(0.5, 0.6)
    with pytest.raises(ABError):
        false_positive_rate(0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.post("/analyse", json={"conv_a": 200, "n_a": 2000, "conv_b": 250, "n_b": 2000}).json()
    assert j["significant"] is True
    assert c.post("/analyse", json={"conv_a": 20, "n_a": 10, "conv_b": 1, "n_b": 10}).status_code == 422
    assert 3700 <= c.get("/sample-size", params={"base_rate": 0.1, "min_lift": 0.02}).json()["per_variant"] <= 3900
    assert c.get("/sample-size", params={"base_rate": 0.9, "min_lift": 0.2}).status_code == 422
    assert c.get("/").status_code == 200
