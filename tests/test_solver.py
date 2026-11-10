from __future__ import annotations

from conftest import make_problem, person
from roster.baseline import round_robin
from roster.fairness import fairness_report, gini, person_stats
from roster.generator import generate
from roster.model import compile_problem
from roster.report import coverage, solve_problem
from roster.rules import violations
from roster.solver import solve


def test_gini_known_values():
    assert gini([3, 3, 3, 3]) == 0
    assert abs(gini([0, 0, 0, 10]) - 0.75) < 1e-9
    assert gini([]) == 0 and gini([0, 0]) == 0


def test_solution_breaks_no_hard_rule_week_and_month(week, month):
    for inst in (week, month):
        res = solve(inst, seed=3)
        assert violations(inst, res.grid) == []


def test_sample_week_is_fully_covered_with_skills(week):
    cov = coverage(week, solve(week, seed=7).grid)
    assert cov["pct_headcount"] == 100.0
    assert cov["pct_skills"] == 100.0
    assert cov["unfilled"] == []


def test_same_seed_gives_same_roster(week):
    a = solve(week, seed=11, iterations=6000).grid
    b = solve(week, seed=11, iterations=6000).grid
    assert a == b


def test_annealing_improves_on_the_greedy_start(week):
    res = solve(week, seed=5)
    assert res.cost < res.greedy_cost


def test_fairness_beats_round_robin(week, month):
    for inst in (week, month):
        mine = fairness_report(person_stats(inst, solve(inst, seed=7).grid))
        naive = fairness_report(person_stats(inst, round_robin(inst)))
        assert mine["score"] > naive["score"] + 20
        assert mine["gini_hours"] < naive["gini_hours"]
        assert mine["gini_unsocial"] < naive["gini_unsocial"]


def test_fewer_unmet_preferences_than_round_robin(month):
    mine = sum(s.unmet for s in person_stats(month, solve(month, seed=7).grid))
    naive = sum(s.unmet for s in person_stats(month, round_robin(month)))
    assert mine < naive / 2


def test_baseline_obeys_hard_rules(week, month):
    for inst in (week, month):
        assert violations(inst, round_robin(inst)) == []


def test_infeasible_demand_is_reported_not_crashed():
    staff = [person("a", ["nurse"]), person("b"), person("c")]
    problem = make_problem(
        staff,
        overrides=[{"day": 2, "kind": "morning", "headcount": 12}, {"day": 3, "kind": "night", "headcount": 1}],
    )
    out = solve_problem(problem, seed=1, iterations=3000)
    assert out["violations"] == []
    assert out["coverage"]["pct_headcount"] < 100
    first = out["coverage"]["unfilled"][0]
    assert first["status"] == "short" and first["reason"]
    assert out["capacity"]["feasible_on_paper"] is False


def test_nobody_holds_required_skill_is_explained():
    problem = make_problem([person("a"), person("b"), person("c"), person("d")])
    out = solve_problem(problem, seed=1, iterations=2000)
    nurse_gaps = [
        s for s in out["coverage"]["unfilled"] if "nurse" in s["skills"] and s["skills"]["nurse"]["have"] == 0
    ]
    assert nurse_gaps and "nobody on the team holds nurse" in nurse_gaps[0]["reason"]


def test_leave_and_day_off_requests_are_respected_when_possible(week):
    res = solve(week, seed=7)
    for p, s in enumerate(week.problem.staff):
        for d in s.leave:
            assert res.grid[p][d] == -1
    stats = person_stats(week, res.grid)
    assert sum(s.off_granted for s in stats) >= 0.7 * sum(s.off_requests for s in stats)


def test_generator_is_deterministic_and_seed_sensitive():
    assert generate(5, 1).model_dump() == generate(5, 1).model_dump()
    assert generate(5, 1).model_dump() != generate(6, 1).model_dump()
    assert generate(5, 4).days == 28


def test_compile_scales_targets_by_period():
    inst = compile_problem(generate(1, 4))
    assert inst.weeks == 4
    assert inst.target[0] == 160
