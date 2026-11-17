from fractions import Fraction

import pytest
from fastapi.testclient import TestClient

from diceodds.api import app
from diceodds.core import DiceError, analyse, at_least, distribution, monte_carlo, parse, presets, stats

c = TestClient(app)


def test_two_d6_by_hand():
    d = distribution("2d6")
    assert d[7] == Fraction(1, 6) and d[2] == Fraction(1, 36) and d[12] == Fraction(1, 36)
    assert sum(d.values()) == 1 and stats(d)[0] == 7.0


def test_standard_deviation_of_3d6():
    assert stats(distribution("3d6"))[1] == pytest.approx((3 * 35 / 12) ** 0.5)


def test_advantage_and_disadvantage():
    adv, dis = distribution("2d20kh1"), distribution("2d20kl1")
    assert adv[20] == Fraction(39, 400) and adv[1] == Fraction(1, 400)
    assert at_least(adv, 11) == Fraction(3, 4)  # 1 - (10/20)^2
    assert at_least(dis, 11) == Fraction(1, 4)  # (10/20)^2
    assert stats(adv)[0] == 13.825 and stats(dis)[0] == 7.175


def test_drop_lowest_mean():
    d = distribution("4d6dl1")
    assert sum(d.values()) == 1 and stats(d)[0] == pytest.approx(15869 / 1296)
    assert min(d) == 3 and max(d) == 18 and d[18] == Fraction(21, 1296)  # 6666 plus five ways with a lower fifth


def test_modifier_shifts_distribution():
    d = distribution("1d8+3")
    assert min(d) == 4 and max(d) == 11 and d[4] == Fraction(1, 8)
    assert min(distribution("1d4-2")) == -1


def test_keep_equals_drop_equivalents():
    assert distribution("3d6kh2") == distribution("3d6dl1")
    assert distribution("3d6kl1") == distribution("3d6dh2")


def test_monte_carlo_agrees_with_exact():
    exact = distribution("4d6dl1")
    mc = monte_carlo("4d6dl1", 60_000)
    assert max(abs(float(exact[v]) - mc.get(v, 0)) for v in exact) < 0.01
    assert monte_carlo("2d6", 1000, seed=3) == monte_carlo("2d6", 1000, seed=3)


def test_analyse_fields():
    a = analyse("2d6", 10, trials=20_000)
    assert a["p_exact"] == "1/6" and a["mean"] == 7.0 and a["mc_max_diff"] < 0.02
    assert len(a["pmf"]) == 11 and a["pmf"][5]["exact"] == "1/6"


def test_validation():
    for bad in ["", "d6", "2d1", "0d6", "21d6", "4d6dl4", "2d20kh3", "abc", "3d6*2"]:
        with pytest.raises(DiceError):
            parse(bad)
    with pytest.raises(DiceError):
        distribution("20d100kh1")


def test_presets_and_api():
    assert len(presets()) == 6
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/odds", params={"expr": "2d20kh1", "target": 15}).json()
    assert r["p_exact"] == "51/100" and r["mean"] == 13.82
    assert c.get("/odds", params={"expr": "oops"}).status_code == 422
    assert len(c.get("/presets").json()["presets"]) == 6 and c.get("/").status_code == 200
