import pytest
from fastapi.testclient import TestClient

from farepass.api import app
from farepass.core import OPTIONS, FareError, Rider, best_option, break_even_rides_per_week, build, cost, load

FARES, RIDERS = load()
by_name = {r.name: r for r in RIDERS}
c = TestClient(app)


def rider(week):
    return Rider("x", (tuple(week),) * 4)


def test_costs_by_hand():
    r = rider([2, 2, 0, 0, 0, 0, 0])  # 4 rides a week, 16 in total
    assert cost(FARES, r, "single") == pytest.approx(16 * 2.75)
    assert cost(FARES, r, "day_pass") == pytest.approx(16 * 2.75)  # 2 rides = 5.50 < 6.00 day pass
    assert cost(FARES, r, "week_pass") == 22 * 4
    assert cost(FARES, r, "weekly_cap") == pytest.approx(16 * 2.75)  # 11.00 a week, under the 24.00 cap
    assert cost(FARES, r, "month_pass") == 80


def test_day_pass_helps_only_when_a_day_has_enough_rides():
    assert cost(FARES, rider([3, 0, 0, 0, 0, 0, 0]), "day_pass") == pytest.approx(4 * 6.0)  # 3 x 2.75 > 6
    assert cost(FARES, rider([2, 0, 0, 0, 0, 0, 0]), "day_pass") == pytest.approx(4 * 5.5)


def test_weekly_cap_never_costs_more_than_singles():
    for r in RIDERS:
        assert cost(FARES, r, "weekly_cap") <= cost(FARES, r, "single") + 1e-9


def test_chosen_option_is_the_cheapest():
    for r in RIDERS:
        best, costs = best_option(FARES, r)
        assert costs[best] == min(costs.values())


def test_sample_recommendations():
    got = {r.name: best_option(FARES, r)[0] for r in RIDERS}
    assert got == {
        "Occasional shopper": "single",
        "Part-time student": "month_pass",
        "Daily commuter": "month_pass",
        "Errand runner": "month_pass",
        "Weekend explorer": "day_pass",
    }


def test_ties_prefer_the_simpler_option():
    assert best_option(FARES, by_name["Occasional shopper"])[0] == "single"  # single, day pass and cap all 44.00


def test_break_even():
    assert break_even_rides_per_week(FARES) == pytest.approx(8.0)


def test_validation():
    with pytest.raises(FareError):
        build({"single": 1}, [])
    ok = {"single": 1, "day_pass": 1, "week_pass": 1, "month_pass": 1, "weekly_cap": 1}
    with pytest.raises(FareError):
        build(ok, [{"name": "a", "weeks": [[1] * 7] * 3}])
    with pytest.raises(FareError):
        build({**ok, "single": 0}, [{"name": "a", "weeks": [[1] * 7] * 4}])


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/choose", json=c.get("/sample").json()).json()
    assert [x["best"] for x in r["riders"]][:2] == ["single", "month_pass"]
    assert r["riders"][3]["saving_vs_single"] == pytest.approx(68.5) and set(r["riders"][0]["costs"]) == set(OPTIONS)
    assert c.get("/").status_code == 200


def test_api_validation():
    assert c.post("/choose", json={"fares": {}, "riders": []}).status_code == 422
