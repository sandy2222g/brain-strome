# Dinner On Time

![demo](docs/demo.png)

## Problem
Cooking a roast with five dishes, one oven and one pair of hands: when do you start each step so everything is ready together?

## Solution
Every dish is a chain of steps (peel, boil, roast, carve), and each step uses a limited resource (oven, hob, hands). The planner schedules backwards from serving time. Each step is placed as late as its resource allows, so food doesn't sit around.

On the sample Sunday roast:

| | Synced plan | Start everything in written order |
|---|---|---|
| Start to serve | **170 min** | 210 min |
| Minutes food waits | **142** | 421 |

## Architecture
```
menu.json / POST body -> core.sync_schedule (backward placement, per-minute resource usage)
                      -> core.sequential_schedule (baseline)
                      -> FastAPI /plan -> static/index.html (SVG lanes: oven, hob, hands)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn dinnersync.api:app --port 8000
pytest -q && ruff check .
docker build -t dinnersync . && docker run -p 8000:8000 dinnersync
```
Endpoints: `GET /health`, `GET /sample`, `POST /plan`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Schedule backwards from serving: the deadline is the fixed point and idle time then falls on the early side, where it costs nothing.
- Longest dishes placed first: they have the least slack, so they get first pick of the oven.
- Whole-minute grid with per-minute usage arrays: simple to read and exact to verify with a capacity test.
- Waiting time counted as gaps plus time after the last step: this measures how long cooked food actually sits.
- Stateless API: nothing to store, so it deploys on any free tier.

## Limitations
- The heuristic is greedy, not optimal, and the span is not guaranteed minimal.
- With one oven, the chicken sits about 65 minutes between roasting and carving while the oven is busy.
- Planning horizon is 600 minutes; steps are fixed-length and have no passive time.
- Menu and timings are invented for the demo (MIT).
