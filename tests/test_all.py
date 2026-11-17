import pytest
from fastapi.testclient import TestClient

from mazelab.api import app
from mazelab.core import GENERATORS, MazeError, compare, dead_ends, generate, solve

c = TestClient(app)


def connected(m) -> bool:
    seen, stack = {(0, 0)}, [(0, 0)]
    while stack:
        for n in m.neighbours(stack.pop()):
            if n not in seen:
                seen.add(n)
                stack.append(n)
    return len(seen) == m.width * m.height


@pytest.mark.parametrize("name", sorted(GENERATORS))
def test_every_generator_makes_a_perfect_maze(name):
    for seed in range(20):
        m = generate(12, 9, name, seed)
        assert len(m.passages) == 12 * 9 - 1  # a spanning tree: exactly one path between any two cells
        assert connected(m)


def test_same_seed_same_maze_different_seed_differs():
    assert generate(10, 10, "kruskal", 3) == generate(10, 10, "kruskal", 3)
    assert generate(10, 10, "kruskal", 3) != generate(10, 10, "kruskal", 4)


def test_solution_is_valid_and_unique_in_a_perfect_maze():
    m = generate(15, 15, "prim", 1)
    paths = [solve(m, k).path for k in ("bfs", "dfs", "astar")]
    assert paths[0] == paths[1] == paths[2]  # only one route exists
    p = paths[0]
    assert p[0] == (0, 0) and p[-1] == (14, 14)
    assert all(b in m.neighbours(a) for a, b in zip(p, p[1:], strict=False))


def test_solvers_on_a_hand_made_corridor():
    from mazelab.core import Maze, edge
    m = Maze(3, 1, frozenset({edge((0, 0), (1, 0)), edge((1, 0), (2, 0))}))
    assert solve(m, "bfs").path == [(0, 0), (1, 0), (2, 0)] and solve(m, "bfs").expanded == 3


def test_astar_never_expands_more_than_bfs_on_open_ish_mazes():
    total_b = total_a = 0
    for s in range(40):
        m = generate(20, 20, "kruskal", s)
        total_b += solve(m, "bfs").expanded
        total_a += solve(m, "astar").expanded
    assert total_a < total_b


def test_generators_have_different_personalities():
    rows = {r["generator"]: r for r in compare(20, 20, 30)}
    assert rows["backtracker"]["length"] > 2 * rows["kruskal"]["length"]  # long winding route
    assert rows["backtracker"]["dead"] < rows["kruskal"]["dead"]  # but fewer dead ends
    assert dead_ends(generate(2, 2, "kruskal", 0)) >= 2


def test_validation():
    for bad in [(1, 5), (5, 99)]:
        with pytest.raises(MazeError):
            generate(*bad)
    with pytest.raises(MazeError):
        generate(5, 5, "nope")
    with pytest.raises(MazeError):
        solve(generate(5, 5), "magic")


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    j = c.get("/maze", params={"width": 8, "height": 6, "algorithm": "prim", "seed": 2}).json()
    assert len(j["passages"]) == 47 and set(j["solutions"]) == {"bfs", "dfs", "astar"}
    assert c.get("/maze", params={"algorithm": "x"}).status_code == 422
    assert c.get("/maze", params={"width": 99}).status_code == 422
    assert len(c.get("/compare").json()["rows"]) == 3 and c.get("/").status_code == 200
