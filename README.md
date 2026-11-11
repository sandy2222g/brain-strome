# Table Seating

![demo](docs/demo.png)

## Problem
Seating a wedding: friends should share a table, feuding relatives must not, and everyone fits.

## Solution
Score a seating: +1 for each liked pair at the same table, -10 for each feuding pair. The planner improves seatings by swapping guests while the score rises (hill climbing), restarted from 25 seeded shuffles. On the sample party (16 guests, 4 tables of 4, 20 friendships, 5 feuds):

| | RSVP order | Planned |
|---|---|---|
| Friend pairs together | 2 of 20 | **15 of 20** |
| Feuding pairs together | 0 | 0 |

The planned result is the best found, not proven optimal.

## Architecture
```
data/guests.json or POST body -> core.build (validate) -> core.plan (hill climbing + restarts) / core.in_order
                              -> FastAPI /seat -> static/index.html (round tables, friend and feud lines)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn seating.api:app --port 8000
pytest -q && ruff check .
docker build -t seating . && docker run -p 8000:8000 seating
```
Endpoints: `GET /health`, `GET /sample`, `POST /seat`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Feud penalty 10 vs like bonus 1: one feud costs more than any table of friends can gain, so feuds are effectively forbidden.
- Hill climbing with restarts: a single run gets stuck in local optima; restarts are cheap at under 60 guests.
- Fixed random seed: the same request always gives the same plan, which makes it testable.
- RSVP order as the baseline: it is what a host does without a tool.
- Guest cap of 60: the swap search is quadratic per pass, and this keeps responses fast on a free tier.

## Limitations
- Heuristic, not exact; it does not prove 15 is the maximum.
- Only pairwise likes and feuds; no table sizes that differ, no "must sit together" groups.
- Guest names and relationships are invented (MIT).
