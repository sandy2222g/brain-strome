# Maze Lab

Three ways to carve a maze, three ways to solve it, compared by measurement.

![demo](docs/demo.png)

## Problem
Maze demos usually show one algorithm. Which generator makes harder mazes, and which solver wastes the least effort?

## Solution
A FastAPI service and canvas page. Generators: recursive backtracker, randomised Kruskal (union-find), randomised Prim. Solvers: BFS, DFS, A* (Manhattan heuristic). `/compare` averages 60 mazes of 25x25 per generator.

## Architecture
```
browser canvas -> GET /maze /compare -> api.py -> core.py (generate, solve, dead_ends, compare)
```

## Measured results (25x25, 60 seeds)
| generator | route length | dead ends | BFS looked at | DFS | A* |
|---|---|---|---|---|---|
| backtracker | 234 | 65 | 387 | 562 | 357 |
| kruskal | 75 | 190 | 523 | 421 | 361 |
| prim | 53 | 198 | 623 | 364 | 377 |

Backtracker mazes have routes about 3x longer with far fewer dead ends; A* is the steadiest solver.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn mazelab.api:app --port 8000
pytest
docker build -t mazelab . && docker run -p 8000:8000 mazelab
```
Deploy: see DEPLOY.md.

## Design decisions
- Passages stored as a set of normalised edges: makes spanning-tree checks one length comparison.
- Seeded `random.Random`: same seed gives the same maze, so results are reproducible.
- Perfect mazes (spanning trees): exactly one route, so all solvers must agree, which tests correctness.
- Stateless API with cached comparison: nothing to persist.

## Limitations
- Route is always top-left to bottom-right; sizes capped at 60x60.
- Perfect mazes only (no loops), so A* shows its advantage mostly through its heuristic, not route choice.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. No external data.
