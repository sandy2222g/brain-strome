import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from busroutes.api import app
from busroutes.construct import naive_baseline, nn_route, savings, sweep
from busroutes.evaluate import Plan, format_clock, route_cost, route_stats, summarise
from busroutes.geometry import Grid, corners
from busroutes.improve import local_search, two_opt
from busroutes.instance import PlanningError, build_problem, generate, instance_to_dict
from busroutes.solver import solve

client = TestClient(app)


@pytest.fixture(scope="module")
def problem():
    return build_problem(generate(7))


@pytest.fixture(scope="module")
def solved(problem):
    return solve(problem)


def assigned(plan):
    return sorted(s for r in plan.routes for s in r)


# --- geometry -------------------------------------------------------------------------------------------------


def test_open_grid_distance_is_manhattan():
    g = Grid(5, 5, 0.5)
    assert g.km_from(g.node(0, 0))[g.node(4, 3)] == pytest.approx(3.5)


def test_blocked_edge_forces_detour():
    g0 = Grid(5, 3, 1.0)
    a, b = g0.node(1, 1), g0.node(2, 1)
    g = Grid(5, 3, 1.0, [(a, b)])
    assert g.km_from(a)[b] == 3.0
    assert g0.km_from(a)[b] == 1.0


def test_cut_off_node_is_infinite():
    g = Grid(3, 2, 1.0, [(0, 1), (3, 4)])
    assert g.km_from(0)[2] == float("inf")
    assert g.path(0, 2) == []


def test_path_matches_distance_and_corners_are_short(problem):
    g = problem.grid
    a, b = problem.node(0), problem.node(problem.n)
    path = g.path(a, b)
    assert (len(path) - 1) * g.spacing_km == pytest.approx(problem.dist[0][problem.n])
    assert len(corners(g, path)) <= len(path)


def test_river_detour_is_longer_than_straight_line(problem):
    g = problem.grid
    far = [i for i, s in enumerate(problem.inst.stops) if s.x >= 19]
    assert far
    for i in far:
        a, b = problem.node(i), problem.node(problem.n)
        assert problem.dist[i][problem.n] > g.straight_km(a, b)
    assert any(problem.dist[i][problem.n] > g.manhattan_km(problem.node(i), problem.node(problem.n)) for i in far)


# --- generator ------------------------------------------------------------------------------------------------


def test_generator_is_deterministic_and_seeded():
    assert generate(3) == generate(3)
    assert generate(3) != generate(4)


def test_generated_town_shape():
    inst = generate(7)
    assert len(inst.stops) == 120
    assert len({(s.x, s.y) for s in inst.stops}) == 120
    assert inst.school not in {(s.x, s.y) for s in inst.stops}
    ids = [i for s in inst.stops for i in s.student_ids]
    assert len(ids) == len(set(ids))


def test_sample_file_matches_generator():
    path = Path(__file__).resolve().parents[1] / "data" / "sample_town.json"
    assert json.loads(path.read_text()) == json.loads(json.dumps(instance_to_dict(generate())))


# --- construction and improvement -----------------------------------------------------------------------------


def test_every_stop_assigned_exactly_once(problem, solved):
    assert assigned(solved) == list(range(problem.n))
    assert not solved.unassigned


def test_capacity_never_exceeded(problem, solved):
    for r in solved.routes:
        assert sum(problem.q[s] for s in r) <= problem.cap


def test_ride_limit_respected_or_flagged(problem, solved):
    for r in solved.used():
        for rep in route_stats(problem, r).stops:
            assert rep.ride_min <= problem.limit or rep.status == "over"
            if rep.status == "over":
                assert rep.reason


def test_default_sample_is_feasible(solved, problem):
    s = summarise(problem, solved)
    assert s["feasible"] and s["stops_over_limit"] == 0


def test_two_opt_never_lengthens_a_route(problem):
    for k in (0, 40, 90):
        route = nn_route(problem, list(range(k, k + 15)))[::-1]
        before = route_cost(problem, route)[0]
        after = route_cost(problem, two_opt(problem, route))[0]
        assert after <= before + 1e-9


def test_local_search_keeps_stops_and_does_not_worsen(problem):
    start = sweep(problem, 8, 0)
    cost = lambda rs: sum(route_cost(problem, r)[0] + 8 * route_cost(problem, r)[1] for r in rs)  # noqa: E731
    better = local_search(problem, start.routes)
    assert sorted(s for r in better for s in r) == list(range(problem.n))
    assert cost(better) <= cost(start.routes) + 1e-9


def test_nearest_neighbour_visits_each_stop_once(problem):
    r = nn_route(problem, list(range(30)))
    assert sorted(r) == list(range(30))


def test_savings_baseline_is_complete_and_within_limits(problem):
    plan = savings(problem)
    assert assigned(plan) == list(range(problem.n))
    for r in plan.routes:
        assert sum(problem.q[s] for s in r) <= problem.cap
        assert route_cost(problem, r)[1] == 0


def test_solution_beats_naive_baseline(problem, solved):
    ours, naive = summarise(problem, solved), summarise(problem, naive_baseline(problem))
    assert ours["total_km"] < naive["total_km"]
    assert ours["longest_ride_min"] < naive["longest_ride_min"]
    assert ours["stops_over_limit"] < naive["stops_over_limit"]
    assert ours["buses_used"] <= naive["buses_used"]


def test_solver_is_deterministic(problem, solved):
    again = solve(problem)
    assert again.routes == solved.routes


# --- times ----------------------------------------------------------------------------------------------------


def test_pickups_work_backwards_from_bell(problem, solved):
    for r in solved.used():
        st = route_stats(problem, r)
        assert st.stops[-1].arrive_min < problem.school_arrival
        arrivals = [s.arrive_min for s in st.stops]
        assert arrivals == sorted(arrivals)
        assert st.stops[0].ride_min == pytest.approx(st.minutes)
    assert format_clock(7 * 60 + 5) == "7:05 am"


# --- what-if --------------------------------------------------------------------------------------------------


def test_removing_a_bus_raises_distance_or_flags_infeasible():
    base = build_problem(generate(7, buses=8))
    fewer = build_problem(generate(7, buses=7))
    a, b = summarise(base, solve(base)), summarise(fewer, solve(fewer))
    assert b["total_km"] > a["total_km"] or not b["feasible"]


def test_closing_a_bridge_does_not_shorten_trips():
    inst = generate(7)
    shut = inst.with_changes(close=("bridge-central",))
    a, b = build_problem(inst), build_problem(shut)
    assert all(b.dist[i][a.n] >= a.dist[i][a.n] for i in range(a.n))
    assert any(b.dist[i][a.n] > a.dist[i][a.n] for i in range(a.n))


# --- validation -----------------------------------------------------------------------------------------------


def test_unknown_road_rejected():
    with pytest.raises(PlanningError):
        generate(7).with_changes(close=("nope",))


def test_capacity_below_largest_stop_rejected():
    with pytest.raises(PlanningError):
        build_problem(generate(7, capacity=8).with_changes(capacity=3))


def test_too_few_stops_rejected():
    with pytest.raises(PlanningError):
        generate(7, n_stops=2)


def test_closing_every_bridge_is_reported():
    inst = generate(7).with_changes(close=("bridge-north", "bridge-central", "bridge-south"))
    with pytest.raises(PlanningError):
        build_problem(inst)


def test_empty_plan_summary():
    p = build_problem(generate(7))
    s = summarise(p, Plan([[] for _ in range(3)]))
    assert s["buses_used"] == 0 and s["total_km"] == 0


# --- API ------------------------------------------------------------------------------------------------------


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_sample_endpoint():
    r = client.get("/sample")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["summary"]["feasible"]
    assert body["comparison"]["km_saved_pct"] > 0
    assert len(body["town"]["stops"]) == 120
    first = body["plan"]["routes"][0]["stops"][0]
    assert {"pickup", "ride_min", "status"} <= first.keys()


def test_solve_endpoint_and_validation():
    ok = client.post("/solve", json={"seed": 2, "buses": 9, "capacity": 30})
    assert ok.status_code == 200 and ok.json()["plan"]["summary"]["buses_used"] <= 9
    assert client.post("/solve", json={"buses": 0}).status_code == 422
    assert client.post("/solve", json={"capacity": 5}).status_code == 422
    assert client.post("/solve", json={"close_roads": ["ghost"]}).status_code == 422


def test_whatif_endpoint_removes_a_bus():
    r = client.post("/whatif", json={"base": {}, "change": {"buses": 7}})
    assert r.status_code == 200
    body = r.json()
    assert body["after"]["unserved_students"] > 0 or body["delta"]["total_km"] > 0
    assert body["verdict"]


def test_whatif_close_road():
    r = client.post("/whatif", json={"base": {}, "change": {"close_roads": ["bridge-central"]}})
    assert r.status_code == 200
    assert r.json()["delta"]["total_km"] >= 0
    assert client.post("/whatif", json={"base": {}, "change": {"close_roads": ["x"]}}).status_code == 422
