from __future__ import annotations

from rentcheck.advice import find_alternatives, negotiation_hint, verdict
from rentcheck.model import Range

R = Range(p10=800.0, p50=900.0, p90=1000.0)


def test_verdict_fair() -> None:
    assert verdict(920, R)["key"] == "fair"


def test_verdict_above_market() -> None:
    v = verdict(1200, R)
    assert v["key"] == "above"
    assert v["diff_pct"] > 30
    assert "above" in v["sentence"]


def test_verdict_below_market() -> None:
    assert verdict(600, R)["key"] == "below"


def test_hint_mentions_range_and_ask() -> None:
    hint = negotiation_hint(1200, R)
    assert "€800" in hint and "€1,000" in hint and "€900" in hint


def test_alternatives_are_cheaper_and_elsewhere(listings, flat) -> None:  # type: ignore[no-untyped-def]
    rent = 1500
    alts = find_alternatives(listings, flat, rent, limit=5)
    assert 0 < len(alts) <= 6
    for a in alts:
        assert a["district"] != flat["district"]
        assert a["rent"] < rent
        assert a["saving"] == rent - a["rent"]
        assert a["bedrooms"] == flat["bedrooms"]


def test_alternatives_empty_when_rent_is_tiny(listings, flat) -> None:  # type: ignore[no-untyped-def]
    assert find_alternatives(listings, flat, 50) == []
