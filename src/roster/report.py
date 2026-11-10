"""Turn a grid into the JSON the API returns: assignments with reasons, coverage, people, fairness, baseline."""

from __future__ import annotations

from typing import Any

from .baseline import round_robin
from .explain import assignment_why, gap_reason, unmet_reason
from .fairness import PersonStats, fairness_report, person_stats
from .model import OFF, Grid, Instance, Problem, compile_problem, grid_to_assignments
from .rules import violations
from .solver import solve


def coverage(inst: Instance, grid: Grid, with_reasons: bool = True) -> dict[str, Any]:
    slots = []
    need_total = filled_total = skill_need_total = skill_got_total = 0
    for d in range(inst.D):
        for k in range(inst.K):
            need = inst.need[d][k]
            if need == 0:
                continue
            have = sum(1 for p in range(inst.P) if grid[p][d] == k)
            skills = {}
            for s, req in inst.skill_need[d][k].items():
                got = sum(1 for p in range(inst.P) if grid[p][d] == k and s in inst.skills[p])
                skills[s] = {"need": req, "have": got}
                skill_need_total += req
                skill_got_total += min(req, got)
            short = have < need or any(v["have"] < v["need"] for v in skills.values())
            need_total += need
            filled_total += min(have, need)
            slots.append(
                {
                    "day": d,
                    "kind": inst.kinds[k],
                    "need": need,
                    "filled": have,
                    "skills": skills,
                    "status": "short" if short else "ok",
                    "reason": gap_reason(inst, grid, d, k) if short and with_reasons else "",
                }
            )
    return {
        "slots": slots,
        "unfilled": [s for s in slots if s["status"] == "short"],
        "places_needed": need_total,
        "places_filled": filled_total,
        "pct_headcount": round(100 * filled_total / need_total, 1) if need_total else 100.0,
        "pct_skills": round(100 * skill_got_total / skill_need_total, 1) if skill_need_total else 100.0,
    }


def _people(inst: Instance, grid: Grid, stats: list[PersonStats], with_reasons: bool = True) -> list[dict[str, Any]]:
    out = []
    for p, s in enumerate(stats):
        staff = inst.problem.staff[p]
        unmet = []
        for d in sorted(inst.off_req[p]):
            if grid[p][d] != OFF:
                unmet.append(
                    {
                        "type": "day_off",
                        "day": d,
                        "text": f"Asked for {inst.label(d)} off, working {inst.kinds[grid[p][d]]}",
                        "why": unmet_reason(inst, grid, p, d, grid[p][d]) if with_reasons else "",
                    }
                )
        for d in range(inst.D):
            k = grid[p][d]
            if k != OFF and k in inst.avoid[p]:
                unmet.append(
                    {
                        "type": "avoid",
                        "day": d,
                        "text": f"Asked to avoid {inst.kinds[k]}s, working {inst.label(d)} {inst.kinds[k]}",
                        "why": unmet_reason(inst, grid, p, d, k) if with_reasons else "",
                    }
                )
        out.append(
            {
                "id": s.staff_id,
                "name": s.name,
                "skills": staff.skills,
                "contract": s.contract,
                "hours": s.hours,
                "shifts": s.shifts,
                "weekends": s.weekends,
                "evenings": s.evenings,
                "nights": s.nights,
                "off_requests": s.off_requests,
                "off_granted": s.off_granted,
                "avoid_worked": s.avoid_worked,
                "preferred_worked": s.preferred_worked,
                "preferences_granted": s.granted,
                "unmet_count": s.unmet,
                "unmet": unmet,
            }
        )
    return out


def summarise(inst: Instance, grid: Grid, with_reasons: bool = True) -> dict[str, Any]:
    stats = person_stats(inst, grid)
    cov = coverage(inst, grid, with_reasons)
    fair = fairness_report(stats)
    assigns = []
    for a in grid_to_assignments(inst, grid):
        p = inst.staff_index[a.staff_id]
        why = assignment_why(inst, grid, stats, p, a.day) if with_reasons else ""
        assigns.append({"staff_id": a.staff_id, "day": a.day, "kind": a.kind, "why": why})
    return {
        "assignments": assigns,
        "coverage": cov,
        "people": _people(inst, grid, stats, with_reasons),
        "fairness": fair,
        "unmet_preferences": sum(s.unmet for s in stats),
        "violations": [v.__dict__ for v in violations(inst, grid)],
    }


def capacity_note(inst: Instance) -> dict[str, Any]:
    demand = sum(inst.need[d][k] * inst.hours[k] for d in range(inst.D) for k in range(inst.K))
    avail = 0.0
    for p in range(inst.P):
        days_ok = inst.D - len(inst.leave[p])
        avail += min(inst.target[p] * days_ok / inst.D, inst.D / 7 * inst.problem.rules.max_weekly_hours)
    return {
        "demand_hours": demand,
        "contract_hours_available": round(avail),
        "feasible_on_paper": demand <= avail * 1.2,
    }


def solve_problem(problem: Problem, seed: int = 7, iterations: int | None = None) -> dict[str, Any]:
    inst = compile_problem(problem)
    res = solve(inst, seed, iterations)
    mine = summarise(inst, res.grid)
    base_grid = round_robin(inst)
    base = summarise(inst, base_grid)
    for a in base["assignments"]:
        a["why"] = "Next person in the rotation who was free and allowed; wishes and fairness were not looked at."
    comparison = {
        "fairness_score": {"baseline": base["fairness"]["score"], "solver": mine["fairness"]["score"]},
        "gini_weekend": {"baseline": base["fairness"]["gini_weekend"], "solver": mine["fairness"]["gini_weekend"]},
        "gini_unsocial": {"baseline": base["fairness"]["gini_unsocial"], "solver": mine["fairness"]["gini_unsocial"]},
        "gini_hours": {"baseline": base["fairness"]["gini_hours"], "solver": mine["fairness"]["gini_hours"]},
        "unmet_preferences": {"baseline": base["unmet_preferences"], "solver": mine["unmet_preferences"]},
        "coverage_pct": {"baseline": base["coverage"]["pct_headcount"], "solver": mine["coverage"]["pct_headcount"]},
        "skills_pct": {"baseline": base["coverage"]["pct_skills"], "solver": mine["coverage"]["pct_skills"]},
    }
    return {
        "name": problem.name,
        "days": problem.days,
        "start_weekday": problem.start_weekday,
        "seed": seed,
        "kinds": inst.kinds,
        "solver": {"iterations": res.iterations, "accepted": res.accepted, "seconds": res.seconds},
        "capacity": capacity_note(inst),
        **mine,
        "baseline": base,
        "comparison": comparison,
    }
