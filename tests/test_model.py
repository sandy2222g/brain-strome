from __future__ import annotations

import pytest

from seating.model import APART_PENALTY, Guest, Problem, Scorer, SeatingError, describe, solve


def test_sample_respects_all_hard_rules(problem: Problem) -> None:
    sol = solve(problem, seed=1)
    assert sol.violations == []
    assert sorted(n for t in sol.tables for n in t) == sorted(g.name for g in problem.guests)
    assert all(len(t) <= problem.table_size for t in sol.tables)
    where = {n: i for i, t in enumerate(sol.tables) for n in t}
    for grp in problem.together:
        assert len({where[n] for n in grp}) == 1
    for a, b in problem.apart:
        assert where[a] != where[b]


def test_optimised_beats_random_by_a_wide_margin(problem: Problem) -> None:
    sol = solve(problem, seed=2)
    assert sol.score > sol.random_baseline + 100


def test_deterministic_for_a_seed_and_seed_changes_result(problem: Problem) -> None:
    a, b = solve(problem, seed=5, iterations=5000), solve(problem, seed=5, iterations=5000)
    assert a.tables == b.tables and a.score == b.score
    assert solve(problem, seed=6, iterations=5000).tables != a.tables


def test_dislikes_are_separated_when_possible(problem: Problem) -> None:
    sol = solve(problem, seed=3)
    where = {n: i for i, t in enumerate(sol.tables) for n in t}
    assert all(where[a] != where[b] for a, b in problem.dislikes)


def test_likes_are_seated_together_mostly(problem: Problem) -> None:
    sol = solve(problem, seed=3)
    where = {n: i for i, t in enumerate(sol.tables) for n in t}
    assert all(where[a] == where[b] for a, b in problem.likes)


def test_tiny_problem_exact() -> None:
    p = Problem([Guest("A", "x"), Guest("B", "x"), Guest("C", "y"), Guest("D", "y")], table_size=2)
    sol = solve(p, seed=0)
    assert sorted(sorted(t) for t in sol.tables) == [["A", "B"], ["C", "D"]]


def test_infeasible_together_group() -> None:
    p = Problem([Guest(n) for n in "ABCDE"], together=[list("ABCDE")], table_size=4)
    with pytest.raises(SeatingError, match="must sit together"):
        solve(p)


@pytest.mark.parametrize(
    "problem",
    [
        Problem([]),
        Problem([Guest("A"), Guest("A")]),
        Problem([Guest("A")], likes=[("A", "Z")]),
        Problem([Guest("A")], table_size=0),
    ],
)
def test_validation(problem: Problem) -> None:
    with pytest.raises(SeatingError):
        solve(problem)


def test_describe_flags_violations_and_explains() -> None:
    p = Problem(
        [Guest("A", "g"), Guest("B", "g"), Guest("C")],
        likes=[("A", "B")],
        apart=[("A", "C")],
        together=[["B", "C"]],
        table_size=3,
    )
    bad = describe(p, [["A", "B", "C"]], Scorer(p))
    assert len(bad.violations) == 1 and bad.score < APART_PENALTY / 2
    good = describe(p, [["A", "B"], ["C"]], Scorer(p))
    assert any("together group is split" in v for v in good.violations)
    assert "wanted to sit together" in good.reasons["A"][0]


def test_describe_rejects_bad_arrangements() -> None:
    p = Problem([Guest("A"), Guest("B")], table_size=1)
    with pytest.raises(SeatingError, match="exactly once"):
        describe(p, [["A"]], Scorer(p))
    with pytest.raises(SeatingError, match="more than"):
        describe(p, [["A", "B"]], Scorer(p))
