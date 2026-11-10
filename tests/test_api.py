from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from roster.api import app

client = TestClient(app)


@pytest.fixture(scope="module")
def solved() -> dict:
    return client.post("/solve", json={}).json()


def plain(assigns: list[dict]) -> list[dict]:
    return [{k: a[k] for k in ("staff_id", "day", "kind")} for a in assigns]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_sample_week_and_four_weeks():
    assert client.get("/sample").json()["days"] == 7
    four = client.get("/sample", params={"weeks": 4}).json()
    assert four["days"] == 28 and len(four["staff"]) == 12


def test_sample_rejects_other_lengths():
    assert client.get("/sample", params={"weeks": 3}).status_code == 422


def test_solve_returns_the_full_report(solved):
    for key in ("assignments", "coverage", "people", "fairness", "comparison", "baseline", "violations", "solver"):
        assert key in solved
    assert solved["violations"] == []
    assert solved["comparison"]["fairness_score"]["solver"] > solved["comparison"]["fairness_score"]["baseline"]
    assert all(a["why"] for a in solved["assignments"])
    unmet = [u for p in solved["people"] for u in p["unmet"]]
    assert all(u["why"] for u in unmet)


def test_solve_validates_input():
    assert client.post("/solve", json={"problem": {"staff": []}}).status_code == 422
    assert client.post("/solve", json={"seed": -1}).status_code == 422
    assert client.post("/solve", json={"iterations": 10**9}).status_code == 422


def test_solve_accepts_a_custom_problem_and_reports_gaps():
    problem = client.get("/sample").json()
    problem["overrides"] = [{"day": 1, "kind": "night", "headcount": 9}]
    out = client.post("/solve", json={"problem": problem, "iterations": 2000}).json()
    assert out["coverage"]["pct_headcount"] < 100
    assert out["coverage"]["unfilled"]


def test_swap_check_allows_a_safe_swap_and_blocks_an_unsafe_one(solved):
    assigns = solved["assignments"]
    outcomes = []
    for i, a in enumerate(assigns):
        for b in assigns[i + 1 :]:
            if a["day"] != b["day"]:
                continue
            body = {
                "assignments": plain(assigns),
                "a": {"staff_id": a["staff_id"], "day": a["day"]},
                "b": {"staff_id": b["staff_id"], "day": b["day"]},
            }
            outcomes.append(client.post("/swap-check", json=body).json())
    assert any(o["ok"] for o in outcomes)
    blocked = [o for o in outcomes if not o["ok"]]
    assert blocked and blocked[0]["violations"] and blocked[0]["verdict"].startswith("Blocked")


def test_swap_check_handover_to_someone_off(solved):
    assigns = solved["assignments"]
    a = assigns[0]
    working = {x["staff_id"] for x in assigns if x["day"] == a["day"]}
    free = next(p["id"] for p in solved["people"] if p["id"] not in working)
    body = {
        "assignments": plain(assigns),
        "a": {"staff_id": a["staff_id"], "day": a["day"]},
        "b": {"staff_id": free, "day": a["day"]},
    }
    out = client.post("/swap-check", json=body).json()
    assert out["hours"][free]["after"] == out["hours"][free]["before"] + 8
    assert out["hours"][a["staff_id"]]["after"] == out["hours"][a["staff_id"]]["before"] - 8


def test_swap_check_detects_leave_conflict():
    problem = client.get("/sample").json()
    on_leave = next(s for s in problem["staff"] if s["leave"])
    day = on_leave["leave"][0]
    other = next(s["id"] for s in problem["staff"] if s["id"] != on_leave["id"])
    assigns = [{"staff_id": other, "day": day, "kind": "morning"}]
    body = {
        "problem": problem,
        "assignments": assigns,
        "a": {"staff_id": other, "day": day},
        "b": {"staff_id": on_leave["id"], "day": day},
    }
    out = client.post("/swap-check", json=body).json()
    assert out["ok"] is False
    assert any(v["rule"] == "leave" for v in out["violations"])


def test_swap_check_validation():
    body = {"assignments": [], "a": {"staff_id": "amara", "day": 0}, "b": {"staff_id": "bram", "day": 0}}
    assert client.post("/swap-check", json=body).status_code == 422
    bad = {"assignments": [{"staff_id": "ghost", "day": 0, "kind": "morning"}], **{k: body[k] for k in "ab"}}
    assert client.post("/swap-check", json=bad).status_code == 422
    assert client.post("/swap-check", json={"a": {}}).status_code == 422


def test_index_page_is_served():
    r = client.get("/")
    assert r.status_code == 200 and "Roster board" in r.text
