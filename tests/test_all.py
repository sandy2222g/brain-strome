import pytest
from fastapi.testclient import TestClient

from eloleague.api import app
from eloleague.core import (
    LeagueError,
    evaluate,
    expected,
    leaderboard,
    load_matches,
    predict,
    ranks,
    rate,
    spearman,
    win_rates,
)

c = TestClient(app)


def test_expected_score_by_hand():
    assert expected(1000, 1000) == 0.5
    assert expected(1400, 1000) == pytest.approx(1 / 1.1)  # 10 ** -1 = 0.1
    assert expected(1000, 1400) == pytest.approx(1 - 1 / 1.1)


def test_equal_players_move_twelve_points():
    r, _ = rate([("A", "B")])
    assert r == {"A": 1012.0, "B": 988.0}


def test_upset_moves_more_than_expected_win():
    # A (1000) beats B (1400): gain = 24 * (1 - expected) = 24 * (1 - 1/11)
    ratings, hist = rate([("B", "C"), ("B", "C"), ("B", "C"), ("B", "C"), ("A", "B")])
    before = hist["B"][-2]
    assert ratings["A"] - 1000 == pytest.approx(24 * (1 - expected(1000, before)))
    assert sum(ratings.values()) == pytest.approx(3000)  # zero-sum: ratings only move between players


def test_history_tracks_every_game():
    _, hist = rate([("A", "B"), ("A", "B"), ("B", "A")])
    assert len(hist["A"]) == 4 and hist["A"][0] == 1000.0


def test_spearman_by_hand():
    assert spearman([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)
    assert spearman([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert ranks([1, 2, 2, 3]) == [1.0, 2.5, 2.5, 4.0]
    assert spearman([1, 2, 2, 3], [1, 2, 3, 4]) == pytest.approx(0.9487, abs=1e-4)


def test_win_rates():
    assert win_rates([("A", "B"), ("A", "C"), ("B", "C")]) == {"A": 1.0, "B": 0.5, "C": 0.0}


def test_elo_beats_win_rate_on_unbalanced_schedule():
    e = evaluate()
    assert e["matches"] == 240 and e["holdout"] == 60
    assert e["rank_corr_elo"] == 0.877 and e["rank_corr_winrate"] == 0.775
    assert e["acc_elo"] == 0.733 and e["acc_winrate"] == 0.683
    assert e["rank_corr_elo"] > e["rank_corr_winrate"]


def test_leaderboard_and_predict():
    lb = leaderboard()
    assert lb[0]["player"] == "Ana" and len(lb) == 12 and lb == sorted(lb, key=lambda r: (-r["rating"], r["player"]))
    assert predict("Ana", "Lena")["p_a"] > 0.8
    assert len(load_matches()) == 240


def test_validation():
    with pytest.raises(LeagueError):
        rate([])
    with pytest.raises(LeagueError):
        rate([("A", "A")])
    with pytest.raises(LeagueError):
        predict("Ana", "Nobody")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/leaderboard").json()["players"][0]["player"] == "Ana"
    assert c.get("/predict", params={"a": "Ana", "b": "Ben"}).json()["p_a"] > 0.5
    assert c.get("/predict", params={"a": "Ana", "b": "Ana"}).status_code == 422
    assert c.get("/evaluation").json()["acc_elo"] == 0.733 and c.get("/").status_code == 200
