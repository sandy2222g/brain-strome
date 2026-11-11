# Box Packer

![demo](docs/demo.png)

## Problem
Moving house: each box has a weight limit and a volume limit. Books hit the weight limit long before the box is full; duvets fill the box while weighing nothing. How many boxes do you need, and what goes where?

## Solution
Two-dimensional bin packing, solved three ways on a 22-item flat move (box = 20 kg and 60 L):

| Method | Boxes |
|---|---|
| Fill in listed order, start a new box when full | 14 |
| First-fit decreasing (biggest first) | 11 |
| Exact branch and bound | **10** (equals the weight/volume lower bound, so provably minimal) |

## Architecture
```
data/items.json or POST body -> core.next_fit / first_fit_decreasing / optimal (branch and bound)
                             -> FastAPI /pack -> static/index.html (box cards with weight and volume bars)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn boxpack.api:app --port 8000
pytest -q && ruff check .
docker build -t boxpack . && docker run -p 8000:8000 boxpack
```
Endpoints: `GET /health`, `GET /sample`, `POST /pack`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Two limits, not one: real boxes fail on weight or volume, so ignoring either gives unusable plans.
- Items ranked by their tighter limit: the item that is hardest to place goes first.
- Exact search seeded with the heuristic answer and stopped at the lower bound: most cases finish in milliseconds.
- Identical open boxes skipped in the search: they would only repeat the same work.
- Node limit with an honest `proved_optimal` flag: the API says when it has not proved the minimum.
- Capped at 24 items for the exact solver: beyond that worst-case time grows too fast for a free tier.

## Limitations
- No fragile, room or stacking rules; every item is just a weight and a volume.
- Volumes add up exactly, but real items do not tessellate, so leave slack in practice.
- First-fit decreasing is not always optimal; a test shows a 3-vs-2 case.
- Items are invented (MIT).
