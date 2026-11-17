# Hash Table Lab

Three collision strategies built from scratch and measured against the textbook formulas.

![demo](docs/demo.png)

## Problem
Interviews and textbooks say "linear probing degrades near full", but by how much, and how does it compare with chaining or double hashing?

## Solution
Chaining, linear probing and double hashing implemented in plain Python with probe counting. For each load factor the lab fills a 1,009-slot table, searches for keys that are absent, and compares the average probes with the closed-form expectation.

## Architecture
```
browser bar charts -> GET /curves -> api.py (cached) -> core.py (Chaining, OpenAddressing, theory, measure)
```

## Measured vs theory (unsuccessful search, average probes)
| load | chaining | linear | double |
|---|---|---|---|
| 50% | 1.49 (1.50) | 2.39 (2.50) | 2.01 (2.00) |
| 80% | 1.79 (1.80) | 10.7 (13.0) | 4.82 (5.00) |
| 90% | 1.89 (1.90) | 31.8 (50.5) | 9.96 (10.0) |

Theory in brackets. Linear probing at 90% falls short of the formula, which describes very large tables; chaining and double hashing match closely.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn hashlab.api:app --port 8000
pytest
docker build -t hashlab . && docker run -p 8000:8000 hashlab
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Count probes, not seconds: probe counts are deterministic and match the theory.
- Prime table size (1,009): required for double hashing to reach every slot.
- Measure absent keys: the unsuccessful-search formulas are the sharpest test of each strategy.
- Cache the curves: they are fixed for a given seed, so the API stays fast.

## Limitations
- No deletion or resizing; the tables are fixed-size.
- Integer keys only, with one simple multiplicative hash.
- Results come from a seeded 8-trial average, so small differences from theory are expected.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. All keys are random synthetic integers.
