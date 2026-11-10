from __future__ import annotations

from datetime import date, timedelta

import pytest

from lostfound.features import FEATURE_NAMES, Report, explain, pair_features, place_distance
from lostfound.matcher import BRANDS
from lostfound.text import parse


def test_parse_synonyms_collapse_to_canonical() -> None:
    a = parse("Lost my navy rucksack", BRANDS)
    b = parse("Found a dark blue backpack", BRANDS)
    assert (a.category, a.color) == (b.category, b.color) == ("backpack", "blue")
    assert a.tokens.split()[-2:] == b.tokens.split()[-2:]


def test_parse_brand_extras_and_stopwords() -> None:
    a = parse("I lost a Norvik grey phone with a cracked corner and a sticker on it", BRANDS)
    assert a.brand == "Norvik" and a.category == "phone" and a.color == "grey"
    assert a.extras == {"cracked", "sticker"}
    assert "lost" not in a.tokens.split()


def test_parse_unknown_item() -> None:
    a = parse("Found something shiny", BRANDS)
    assert a.category is None and a.color is None and a.brand is None


def test_longest_phrase_wins() -> None:
    assert parse("water bottle", BRANDS).category == "bottle"
    assert parse("dark blue jacket", BRANDS).color == "blue"


def test_place_distance() -> None:
    assert place_distance("library", "library") == 0
    assert place_distance("library", "cafeteria") < place_distance("library", "sports field")
    assert place_distance("library", "nowhere") == 6.0


def _r(desc: str, d: str, place: str = "library") -> Report:
    return Report(date.fromisoformat(d), place, parse(desc, BRANDS))


def test_pair_features_flags() -> None:
    lost = _r("lost my red Pico wallet", "2026-10-01")
    same = _r("found red Pico wallet", "2026-10-03")
    other = _r("found blue Alder phone", "2026-09-28", "car park")
    f_same = dict(zip(FEATURE_NAMES, pair_features(lost, same, 0.9), strict=True))
    f_other = dict(zip(FEATURE_NAMES, pair_features(lost, other, 0.1), strict=True))
    assert f_same["same_category"] == f_same["same_color"] == f_same["same_brand"] == 1
    assert f_same["days_gap"] == 2 and f_same["found_before_lost"] == 0
    assert f_other["category_conflict"] == f_other["color_conflict"] == f_other["brand_conflict"] == 1
    assert f_other["found_before_lost"] == 1


def test_explain_lists_reasons() -> None:
    lost = _r("lost my red Pico wallet with a sticker", "2026-10-01")
    found = _r("found red Pico billfold with a sticker", "2026-10-02")
    reasons = " | ".join(explain(lost, found))
    for needle in ("wallet", "red", "Pico", "sticker", "1 day", "same spot"):
        assert needle in reasons


@pytest.mark.parametrize("gap", [-3, 0, 45])
def test_days_gap_is_clipped(gap: int) -> None:
    lost = _r("lost phone", "2026-10-10")
    found = Report(lost.when + timedelta(days=gap), "library", parse("found phone", BRANDS))
    idx = FEATURE_NAMES.index("days_gap")
    assert 0 <= pair_features(lost, found, 0.5)[idx] <= 30
