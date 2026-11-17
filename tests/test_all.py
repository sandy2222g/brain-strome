import pytest
from fastapi.testclient import TestClient

from trailpath.api import app
from trailpath.core import Grid, TrailError, evaluate, maps, path_cost, solve

c = TestClient(app)
DETOUR = "S^G\n...\n"  # straight over a hill costs 5 + 1 = 6; going round costs 1 + 1 + 1 + 1 = 4


def test_straight_line_cost_by_hand():
    r = solve("S.G", "dijkstra")
    assert r["cost"] == 2 and r["steps"] == 2 and r["path"] == [[0, 0], [0, 1], [0, 2]]


def test_bfs_minimises_steps_but_not_cost():
    bfs, dij = solve(DETOUR, "bfs"), solve(DETOUR, "dijkstra")
    assert bfs["steps"] == 2 and bfs["cost"] == 6  # shortest in steps, over the hill
    assert dij["steps"] == 4 and dij["cost"] == 4  # cheaper in effort, longer in steps


def test_astar_matches_dijkstra_cost_on_every_map():
    for m in maps():
        assert solve(m["text"], "astar")["cost"] == solve(m["text"], "dijkstra")["cost"]


def test_astar_expands_fewer_cells_than_dijkstra():
    rows = evaluate()
    assert all(r["astar"]["expanded"] <= r["dijkstra"]["expanded"] for r in rows)
    assert rows[2]["astar"]["expanded"] == 183 and rows[2]["dijkstra"]["expanded"] == 435


def test_bfs_paths_cost_more_on_uneven_terrain():
    rows = evaluate()
    assert all(r["bfs"]["cost"] >= r["dijkstra"]["cost"] for r in rows)
    assert rows[2]["bfs"]["cost"] == 118 and rows[2]["dijkstra"]["cost"] == 56


def test_unreachable_goal():
    r = solve("S#G", "astar")
    assert r["found"] is False and r["path"] == [] and r["cost"] is None


def test_path_cost_counts_cells_entered():
    g = Grid(DETOUR)
    assert path_cost(g, [(0, 0), (0, 1), (0, 2)]) == 6 and path_cost(g, [(0, 0)]) == 0


def test_water_and_walls_are_blocked():
    assert solve("S~G\n...", "dijkstra")["cost"] == 4
    assert solve("S#G\n.#.", "dijkstra")["found"] is False


def test_validation():
    for bad in ["", "S.\n..G.", "..G", "S.G\nS.G", "S.G?", "S" + "." * 90 + "G"]:
        with pytest.raises(TrailError):
            Grid(bad)
    with pytest.raises(TrailError):
        solve("S.G", "dfs")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    d = c.get("/maps").json()
    assert len(d["maps"]) == 4 and len(d["evaluation"]) == 4
    r = c.post("/solve", json={"text": DETOUR, "algorithm": "astar"}).json()
    assert r["cost"] == 4 and r["expanded"] >= 5
    assert c.post("/solve", json={"text": "nope", "algorithm": "astar"}).status_code == 422
    assert c.get("/").status_code == 200
