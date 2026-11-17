import pytest
from fastapi.testclient import TestClient

from countdown.api import app
from countdown.core import CountdownError, evaluate, random_puzzle, solvable_share, solve

c = TestClient(app)


def test_classic_puzzle_is_solved_exactly_and_the_expression_checks_out():
    r = solve([100, 75, 50, 25, 6, 3], 952)  # a well-known hard example
    assert r["exact"] and evaluate(str(r["expression"])) == 952


def test_expression_uses_only_given_numbers_each_at_most_once():
    import re
    nums = [8, 7, 3, 2, 1, 9]
    r = solve(nums, 343)
    used = sorted(int(x) for x in re.findall(r"\d+", str(r["expression"])))
    pool = sorted(nums)
    for u in used:
        pool.remove(u)  # raises if a number is used more times than offered


def test_small_cases_by_hand():
    assert solve([2, 3], 5)["exact"] and solve([2, 3], 6)["exact"] and solve([2, 3], 1)["exact"]
    assert not solve([2, 3], 7)["exact"] and solve([2, 3], 7)["distance"] == 1  # closest is 6


def test_division_must_be_exact():
    assert not solve([7, 2], 3)["exact"]  # 7/2 is not an integer
    assert solve([8, 2], 4)["exact"]


def test_unreachable_target_returns_the_closest():
    r = solve([1, 1], 999)
    assert not r["exact"] and r["value"] == 2 and r["distance"] == 997


def test_most_random_games_are_solvable():
    assert solvable_share(20) >= 0.8


def test_puzzles_are_deterministic_and_valid():
    p = random_puzzle(5)
    assert p == random_puzzle(5) and len(p["numbers"]) == 6 and 101 <= p["target"] <= 999


def test_evaluate_rejects_dangerous_text():
    for bad in ("__import__('os')", "1; 2", "abc", ""):
        with pytest.raises(CountdownError):
            evaluate(bad)


def test_validation_and_api():
    for bad in [([1], 5), ([1, 2, 3, 4, 5, 6, 7], 5), ([0, 5], 5), ([2, 3], 1000)]:
        with pytest.raises(CountdownError):
            solve(*bad)
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/solve", params={"numbers": "50,25,3,7", "target": 353}).json()
    assert j["exact"] and evaluate(j["expression"]) == 353
    assert c.get("/solve", params={"numbers": "a,b", "target": 5}).status_code == 422
    assert c.get("/puzzle").json()["target"] > 100 and c.get("/").status_code == 200
