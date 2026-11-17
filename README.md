# k-means Lab

k-means clustering written from scratch, with a demonstration of why initialisation matters and how to pick the number of clusters.

![demo](docs/demo.png)

## Problem
k-means is easy to call from a library and easy to misuse: results depend on the starting centres and on a choice of k that the algorithm does not make for you.

## Solution
Pure-Python k-means with two initialisations (random and k-means++). The lab clusters 240 synthetic shoppers (visits vs spend, four hidden groups), plots the elbow curve for k = 1 to 8, and runs each initialisation 60 times to count bad outcomes.

## Architecture
```
browser SVG -> GET /cluster /summary -> api.py -> core.py (blobs, init_random, init_pp, kmeans, elbow, compare_inits)
```

## Measured (60 runs, k = 4)
| start | avg inertia | runs more than 50% worse than best |
|---|---|---|
| random | 462.2 | 25% |
| k-means++ | 412.5 | 13.3% |

Elbow: inertia falls 4408 -> 1996 -> 818 -> 355 for k = 1..4, then barely moves (317, 283, ...).

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn kmeanslab.api:app --port 8000
pytest
docker build -t kmeanslab . && docker run -p 8000:8000 kmeanslab
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Pure Python, no numpy: keeps the algorithm readable and the image small.
- Seeded runs: every number above is reproducible.
- Count "bad runs" instead of only averages: the failure mode of k-means is occasional bad local minima.
- Synthetic blobs with known centres: lets a test check the algorithm recovers the truth.

## Limitations
- Only 2-D points and Euclidean distance; speed is fine for hundreds of points, not millions.
- k-means++ still gives bad runs about 13% of the time here; practical code uses several restarts.
- Elbow reading is visual, not automatic.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. All data is synthetic.
