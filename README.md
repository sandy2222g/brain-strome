# Race Pace Planner

![demo](docs/demo.png)

## Problem
Holding one even speed on a hilly course wastes effort: you burn it on climbs where it buys little speed. Where should a runner spend a fixed amount of effort to finish soonest?

## Solution
Model effort per kilometre as terrain factor x speed squared (uphill factor 1 + 8 x grade, downhill 1 + 3 x grade, floor 0.5). Minimising total time for a fixed total effort has a closed form from Lagrange multipliers: speed on each kilometre is proportional to terrain factor^(-1/3). On the sample hilly 10 km course, with a budget equal to holding 11 km/h evenly:

| | Time | Effort used |
|---|---|---|
| Even speed (11.0 km/h) | 54:33 | 100% |
| Hill-aware speeds (9.8 km/h on the 8% climb, 12.7 km/h on the -8% descent) | **53:59** | 100% |

That is 34 seconds (about 1%) faster for exactly the same effort. The gain is real but modest; on a flat course it is zero, and a test checks that.

## Architecture
```
data/course.json or POST body -> core.build -> core.budget_for_even_speed
                              -> core.even_plan / core.optimal_plan -> FastAPI /plan -> static/index.html (profile + speeds)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn pacer.api:app --port 8000
pytest -q && ruff check .
docker build -t pacer . && docker run -p 8000:8000 pacer
```
Endpoints: `GET /health`, `GET /sample`, `POST /plan`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Closed-form optimum: no solver or library needed, and a test shows 300 random perturbations never beat it.
- Same effort for both plans: the comparison is fair, only the distribution differs.
- Effort budget defined from an even-pace speed: runners know what pace they can hold, not an abstract energy number.
- Speed squared effort: the simplest cost that makes slowing down on hills pay off.
- Terrain floor of 0.5 on descents: very steep downhills do not give unlimited free speed.

## Limitations
- The effort model is an assumption; real physiology (fatigue, braking on steep descents) is not modelled.
- Speeds change instantly at segment edges; no acceleration.
- Course and budget are invented (MIT).
