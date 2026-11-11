# Chore Rota

![demo](docs/demo.png)

## Problem
Housemates rotate chores in a fixed cycle. It is "fair" on paper, but it ignores that one person hates the bathroom and another does not mind it, and that chores differ in effort.

## Solution
Each week the planner picks the best assignment of chores to people. Cost is the person's dislike of the chore (1-5), plus a quadratic penalty on their running workload, plus a nudge against repeating last week's chore. On the sample household (4 people, 4 chores, 8 weeks):

| | Fair rota | Round-robin |
|---|---|---|
| Total dislike | **59** | 90 |
| Effort spread (busiest minus lightest, of 80 pts) | 2 | 0 |
| Longest run on one chore | 1 week | 1 week |

Round-robin is perfectly balanced over full cycles; the fair rota trades a 2-point spread for 34% less dislike.

## Architecture
```
data/household.json or POST body -> core.fair_rota (exact best assignment per week) / core.round_robin
                                 -> FastAPI /rota -> static/index.html (week-by-chore calendar)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn chorerota.api:app --port 8000
pytest -q && ruff check .
docker build -t chorerota . && docker run -p 8000:8000 chorerota
```
Endpoints: `GET /health`, `GET /sample`, `POST /rota`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Quadratic workload penalty: a linear one is constant when everyone works every week, so it changes nothing (found by testing).
- Exact assignment each week by trying all assignments: at most 7 people, so it is fast and cannot be beaten.
- Greedy week by week, not whole-schedule optimal: the rota can be extended or edited week by week.
- Repeat penalty: the cheapest assignment would otherwise hand the same chore to the same person every week.
- `balance` is a request parameter: households can choose their own trade-off between happiness and evenness.

## Limitations
- Spread is not exactly zero; raising `balance` narrows it but raises dislike.
- Needs at least as many people as chores, and dislike scores are self-reported.
- No holidays or swaps; the household is invented (MIT).
