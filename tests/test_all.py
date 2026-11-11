import pytest
from fastapi.testclient import TestClient

from recall.api import app
from recall.core import Card, DeckError, _simulate, build, compare, load

CARDS, DAYS = load()
RESULT = compare(CARDS, DAYS)
c = TestClient(app)


def test_simulation_is_deterministic_for_a_seed():
    assert _simulate("sm2", CARDS, DAYS, 3) == _simulate("sm2", CARDS, DAYS, 3)


def test_daily_reviews_every_card_every_day():
    assert RESULT["daily"]["reviews"] == len(CARDS) * DAYS
    assert RESULT["fixed"]["reviews"] == len(CARDS) * (DAYS // 3)


def test_spacing_recalls_far_more_than_fixed_three_day_reviews():
    assert RESULT["sm2"]["recall"] > RESULT["fixed"]["recall"] + 0.4
    assert RESULT["leitner"]["recall"] > RESULT["fixed"]["recall"] + 0.3


def test_sm2_gets_close_to_daily_review_with_less_than_half_the_reviews():
    assert RESULT["sm2"]["reviews"] < 0.5 * RESULT["daily"]["reviews"]
    assert RESULT["sm2"]["recall"] > RESULT["daily"]["recall"] - 0.15


def test_sample_numbers_are_stable():
    assert round(RESULT["sm2"]["recall"], 2) == 0.85 and round(RESULT["daily"]["recall"], 2) == 0.94
    assert round(RESULT["sm2"]["reviews_per_card"]) == 27


def test_easy_deck_needs_fewer_reviews_than_hard_deck_under_sm2():
    easy = compare([Card(f"e{i}", 0.5) for i in range(6)], 60, seeds=20)["sm2"]["reviews"]
    hard = compare([Card(f"h{i}", 3.0) for i in range(6)], 60, seeds=20)["sm2"]["reviews"]
    assert easy < hard


def test_validation():
    with pytest.raises(DeckError):
        build([], 60)
    with pytest.raises(DeckError):
        build([Card("a", 1.0)], 3)
    with pytest.raises(DeckError):
        build([Card("a", 1.0), Card("a", 1.0)], 60)
    with pytest.raises(DeckError):
        build([Card("a", 9.0)], 60)
    with pytest.raises(DeckError):
        _simulate("magic", CARDS, DAYS, 0)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    body = c.get("/sample").json()
    r = c.post("/compare", json={"cards": body["cards"], "days": body["days"]}).json()
    assert set(r["strategies"]) == {"daily", "fixed", "leitner", "sm2"} and r["cards"] == 12
    assert r["strategies"]["sm2"]["recall"] > r["strategies"]["fixed"]["recall"]
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/compare", json={"cards": [], "days": 60}).status_code == 422
    assert c.post("/compare", json={"cards": [{"name": "a", "hardness": 1}], "days": 3}).status_code == 422
