import math

import pytest
from fastapi.testclient import TestClient

from raffleodds.api import app
from raffleodds.core import (
    Game,
    OddsError,
    analyse,
    expected_value,
    load_games,
    p_matches,
    raffle,
    simulate,
    tiers,
)

c = TestClient(app)
GAMES = load_games()
SIX, DAILY = GAMES[0], GAMES[2]


def test_jackpot_odds_by_hand():
    assert math.comb(45, 6) == 8_145_060
    assert p_matches(SIX, 6) == pytest.approx(1 / 8_145_060)
    assert p_matches(SIX, 0) == pytest.approx(3_262_623 / 8_145_060)  # C(39,6) / C(45,6)


def test_probabilities_sum_to_one():
    for g in GAMES:
        assert sum(p_matches(g, m) for m in range(g.k + 1)) == pytest.approx(1.0)


def test_expected_value_by_hand():
    # Daily Pick: (1500*1 + 10*64 + 1*720) / 4845 per 1.00 ticket
    ev = expected_value(DAILY)
    assert ev["return_per_ticket"] == pytest.approx(2860 / 4845)
    assert ev["net_per_ticket"] == pytest.approx(2860 / 4845 - 1)
    assert ev["p_any_prize"] == pytest.approx((1 + 64 + 720) / 4845)


def test_every_sample_game_loses_money_on_average():
    assert all(expected_value(g)["payout_rate"] < 1 for g in GAMES)
    assert round(expected_value(SIX)["payout_rate"], 3) == 0.325


def test_tiers_include_zero_matches():
    t = tiers(DAILY)
    assert [x["matches"] for x in t] == [4, 3, 2, 1, 0] and t[0]["one_in"] == pytest.approx(4845)


def test_simulation_tracks_expected_value_and_is_seeded():
    s = simulate(DAILY, 200, 1000)
    assert abs(s["mean_net"] / 200 - expected_value(DAILY)["net_per_ticket"]) < 0.25
    assert simulate(DAILY, 50, 100, seed=5) == simulate(DAILY, 50, 100, seed=5)
    assert s["worst"] >= -200 and s["worst"] <= s["median_net"] <= s["best"]
    assert sum(b["count"] for b in s["hist"]) == 1000


def test_most_people_lose_over_a_decade_of_weekly_tickets():
    s = analyse(0, 520)["sim"]
    assert s["share_ahead"] < 0.05 and s["median_net"] < -800


def test_raffle_by_hand():
    r = raffle(500, 10, 200, 2)
    assert r["p_win"] == 0.02 and r["expected_prize"] == 4.0 and r["net"] == -16.0 and r["break_even_prize"] == 1000.0


def test_validation():
    with pytest.raises(OddsError):
        Game("x", 5, 6, 1.0, {})
    with pytest.raises(OddsError):
        Game("x", 10, 3, 1.0, {4: 5.0})
    with pytest.raises(OddsError):
        simulate(DAILY, 5000, 5000)
    with pytest.raises(OddsError):
        raffle(10, 11, 5, 1)
    with pytest.raises(OddsError):
        analyse(9, 10)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    assert len(c.get("/games").json()["games"]) == 3
    r = c.get("/analyse", params={"game": 2, "tickets": 100}).json()
    assert r["tiers"][0]["matches"] == 4 and r["sim"]["tickets"] == 100
    assert c.get("/analyse", params={"game": 7}).status_code == 422
    assert c.get("/raffle", params={"tickets_sold": 500, "mine": 10, "prize": 200, "price": 2}).json()["net"] == -16.0
    assert c.get("/raffle", params={"tickets_sold": 5, "mine": 9, "prize": 1, "price": 1}).status_code == 422
    assert c.get("/").status_code == 200
