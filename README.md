# Rate Limiter Lab

Three rate limiting algorithms, run on the same simulated traffic and compared.

![demo](docs/demo.png)

## Problem
Every API needs rate limiting, but "10 requests per 10 seconds" means different things depending on the algorithm.

## Solution
Pure-Python implementations of fixed window, sliding window log and token bucket, driven by simulated time (no sleeping, fully deterministic). A page replays steady, bursty and window-edge traffic through each and shows what was allowed.

## Architecture
```
browser canvas -> GET /compare?kind= -> api.py -> core.py (FixedWindow, SlidingLog, TokenBucket, traffic, simulate, worst_span)
```

## Measured (limit 10 per 10 s, 60 s of traffic, edge pattern)
| algorithm | allowed of 100 | worst 10 s span |
|---|---|---|
| fixed window | 60 | 20 |
| sliding log | 50 | 10 |
| token bucket | 50 | 14 |

Fixed window lets double the limit through at a window boundary; sliding log never does.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn ratelab.api:app --port 8000
pytest
docker build -t ratelab . && docker run -p 8000:8000 ratelab
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Simulated clock passed into `allow(t)`: tests are instant and deterministic.
- `worst_span` as the metric: it measures the actual guarantee a limiter gives.
- Sliding log as the exactness oracle: simplest correct algorithm to compare the others against.
- Seeded traffic generators: identical results on every run.

## Limitations
- Single process, in memory; a real deployment would need shared state such as Redis.
- Token bucket may allow up to capacity plus refill in one span by design.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. All traffic is synthetic.
