# Terrain Trail Pathfinder

**Problem.** "Shortest route" can mean fewest steps or least effort, and they are not the same on uneven ground. A path-finder that counts steps happily marches straight over a hill that a cheaper detour would avoid.

**Solution.** Three classic algorithms run on the same weighted maps (roads cost 1, sand 3, hills 5; water and walls block): breadth-first search (fewest steps), Dijkstra (least effort) and A* (least effort, guided toward the goal by a Manhattan-distance estimate). The page draws the map, every cell each algorithm examined, and the route it chose.

![demo](docs/demo.png)

**Measured result.** On four 34x18 maps BFS routes cost up to **2.1x** the optimum (hill country: effort 118 vs 56). A* finds exactly the same optimal cost as Dijkstra while examining **5-58% fewer cells** (hill country: 183 vs 435; meadow: 281 vs 455; the maze-like map has almost nothing to prune: 370 vs 391).

## Data
`data/maps.json`: four ASCII terrain maps generated for this repo from seeded random patches and walls, re-seeded until a route exists. No real geography.

## Architecture
```
static/index.html --POST /solve, GET /maps--> api.py (FastAPI) --> core.Grid (parse + validate)
                                                                  --> core.bfs / core.best_first (Dijkstra, A*)
                                                                  data/maps.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn trailpath.api:app --reload
pytest && ruff check .
docker build -t trailpath . && docker run -p 8000:8000 trailpath
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Cost is paid for the cell you enter: the start cell is free, which keeps costs equal to "sum of cells on the route minus the start".
- One `best_first` function for Dijkstra and A*: A* is Dijkstra with a heuristic, so the code shows they differ by one term.
- Manhattan heuristic: admissible and consistent because every step costs at least 1, so A* is guaranteed optimal; a test checks equal cost on every map.
- Lazy deletion in the priority queue: simpler than decrease-key and fast enough for maps up to 80x80.
- Map size capped at 80x80: a public endpoint should not accept a million-cell grid.

## Limitations
4-direction movement only (no diagonals); costs are small integers; the heuristic is weak when expensive terrain is everywhere, so A* barely beats Dijkstra on the maze-like map; synthetic maps. MIT licence.
