# Cache Policy Lab

FIFO, LRU and LFU eviction compared against Belady's optimal policy on three kinds of traffic.

![demo](docs/demo.png)

## Problem
Every cache must decide what to evict. Which policy is best depends on the access pattern, and it is hard to know how much better you could do.

## Solution
Four policies implemented from scratch and replayed over seeded synthetic traces (Zipf popularity, uniform, and hot set with scans). Belady's optimal policy, which uses the future, gives an upper bound so every result has context.

## Architecture
```
browser SVG chart -> GET /curve?kind= -> api.py -> core.py (fifo, lru, lfu, optimal, make_trace, curve)
```

## Measured (cache size 20, 5,000 requests)
| trace | fifo | lru | lfu | optimal |
|---|---|---|---|---|
| zipf | 40.0% | 45.7% | 55.9% | 66.7% |
| uniform | 10.1% | 9.9% | 10.4% | 37.5% |
| scan | 62.4% | 62.4% | 71.1% | 71.1% |

## Verified
- Belady's anomaly reproduced for FIFO on the classic trace (3 slots: 3 hits; 4 slots: 2 hits).
- Optimal matches an exhaustive brute-force search on small traces.
- Optimal is never beaten by any policy across 90 random traces.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn cachelab.api:app --port 8000
pytest
docker build -t cachelab . && docker run -p 8000:8000 cachelab
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Policies return hit counts over a trace: the simplest interface that makes comparison fair.
- Belady as a bound: shows how much headroom is left, not just who wins.
- Seeded traces: results are reproducible.
- LFU ties broken by recency: avoids arbitrary behaviour.

## Limitations
- Traces are synthetic; real workloads differ (and modern caches such as ARC or TinyLFU are not covered).
- Hit rate only; no latency, size-weighted cost or expiry.
- LFU eviction is O(n) per miss, fine for a lab but not production.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. All data is synthetic.
