# Taxi Fare Splitter

![demo](docs/demo.png)

## Problem
Five people share a taxi from the station and get off at different stops. Equal split is unfair to the person who gets off first; splitting by own distance ignores that one passenger's far-off stop drags everyone on a detour.

## Solution
Charge each rider their Shapley value: the average extra fare they cause, over every order in which the riders could have been picked up. The cost of any group is the cheapest route from the station through its stops, found exactly. On the sample ride (fare $22.47):

| | Equal | By distance | Shapley |
|---|---|---|---|
| Ana (near) | $4.49 | $1.39 | **$0.87** |
| Chen (far) | $4.49 | $6.30 | **$4.83** |
| Eli (detour) | $4.49 | $5.61 | **$9.20** |
| Riders paying more than riding alone | **2** | 0 | 0 |

Shapley always sums to the true fare and never charges anyone more than going alone; Eli, who adds a long detour, pays most.

## Architecture
```
data/ride.json or POST body -> core.build -> core.group_cost (cheapest open route, cached)
                            -> core.shapley / equal_split / distance_split -> FastAPI /split -> static/index.html
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn farefair.api:app --port 8000
pytest -q && ruff check .
docker build -t farefair . && docker run -p 8000:8000 farefair
```
Endpoints: `GET /health`, `GET /sample`, `POST /split`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Shapley value: it is the only split that is efficient, symmetric and gives nothing to a rider who adds no cost.
- Exact cheapest route for each group: trying every stop order is exact and cheap at 7 riders or fewer.
- Cached group costs: the Shapley sum revisits the same groups many times.
- Straight-line distance: no map data or API keys needed; a road-distance function can replace it.
- Both naive rules shown: the comparison is what makes the fairness point.

## Limitations
- Capped at 7 riders: the Shapley sum has n! orders and each needs route searches.
- Straight-line distances on a flat plane, a single vehicle and no waiting charges.
- Riders and stops are invented (MIT).
