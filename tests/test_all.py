import pytest
from fastapi.testclient import TestClient

from cellauto.api import app
from cellauto.core import (
    PATTERNS,
    AutomataError,
    classify,
    complexity,
    life_run,
    life_step,
    normalise,
    population_curve,
    rule_row,
    rule_table,
    run_rule,
)

c = TestClient(app)


def show(rows: list[list[int]]) -> list[str]:
    return ["".join(".#"[v] for v in r) for r in rows]


def test_rule_30_first_rows_by_hand():
    assert show(run_rule(30, 4, 9)) == ["....#....", "...###...", "..##..#..", ".##.####."]


def test_rule_30_centre_column_matches_the_published_sequence():
    centre = [r[20] for r in run_rule(30, 16, 41)]
    assert centre == [1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1]  # OEIS A051023


def test_rule_90_makes_a_sierpinski_triangle():
    rows = run_rule(90, 64, 129)
    assert [sum(rows[n]) for n in (0, 1, 3, 7, 15, 31, 63)] == [1, 2, 4, 8, 16, 32, 64]
    assert sum(rows[5]) == 2 ** bin(5).count("1")  # row n has 2^(binary ones in n) cells


def test_trivial_rules():
    assert sum(map(sum, run_rule(0, 10, 11))) == 1  # everything dies after the seed row
    assert rule_row(255, [0, 0, 0]) == [1, 1, 1] and rule_row(204, [1, 0, 1]) == [1, 0, 1]  # 204 copies the cell


def test_complexity_ranks_chaos_above_boredom():
    t = {r["rule"]: r["complexity"] for r in rule_table()}
    assert t[30] > 5 * t[0] and t[30] > t[90] > t[0]
    top = sorted(t, key=lambda r: -t[r])[:6]
    assert {30, 86, 135, 149} <= set(top)  # rule 30 and its mirror and complement twins
    assert complexity([[0] * 50] * 50) < 0.05


def test_life_rules_on_tiny_cases():
    assert life_step({(0, 0)}) == set()  # a lone cell dies
    assert life_step(set(PATTERNS["block"])) == set(PATTERNS["block"])  # still life
    assert life_step({(0, 0), (1, 0), (2, 0)}) == {(1, -1), (1, 0), (1, 1)}  # blinker flips


def test_classification_of_famous_patterns():
    assert classify("block")["kind"] == "still life"
    for p in ("blinker", "toad", "beacon"):
        assert classify(p)["kind"] == "oscillator" and classify(p)["period"] == 2
    g, w = classify("glider"), classify("lwss")
    assert g["kind"] == w["kind"] == "spaceship" and g["period"] == w["period"] == 4
    assert g["move"] == [1, 1] and w["move"] == [-2, 0]  # glider c/4 diagonally, spaceship c/2


def test_r_pentomino_settles_after_1103_generations_with_116_cells():
    curve = population_curve("r-pentomino", 1103)
    assert curve[0] == 5 and curve[-1] == 116  # the textbook result
    assert curve[-4:] == [122, 118, 118, 116]  # still changing just before the last collisions end


def test_normalise_and_validation():
    assert normalise({(5, 7), (6, 7)}) == frozenset({(0, 0), (1, 0)}) and normalise(set()) == frozenset()
    for bad in [(256, 10, 11), (30, 0, 11), (30, 10, 10), (30, 10, 2)]:
        with pytest.raises(AutomataError):
            run_rule(*bad)
    with pytest.raises(AutomataError):
        life_run("nope", 3)


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    r = c.get("/rule", params={"rule": 90, "steps": 8, "width": 31}).json()
    assert len(r["rows"]) == 8 and r["rows"][0].count("1") == 1
    assert c.get("/rule", params={"rule": 999}).status_code == 422
    top = c.get("/rules/top").json()["top"]
    assert top[0]["rule"] == 30
    g = c.get("/life", params={"pattern": "glider", "gens": 8}).json()
    assert len(g["frames"]) == 9 and g["info"]["kind"] == "spaceship"
    assert c.get("/life", params={"pattern": "x"}).status_code == 422
    assert len(c.get("/patterns").json()["patterns"]) == 7 and c.get("/").status_code == 200
