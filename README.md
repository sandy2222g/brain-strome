# Countdown Solver

Solves the "Countdown" numbers game: reach a target from six numbers using +, -, x and exact division, each number used at most once.

![demo](docs/demo.png)

## Problem
Finding a route to the target by hand is slow, and when none exists you want the closest answer plus proof the search was complete.

## Solution
An exhaustive search: repeatedly pick two numbers, combine them every legal way, and recurse on the smaller set. Repeated number sets are skipped (memoised). The solver returns the closest reachable value and an expression for it, and `evaluate` re-checks that expression with a whitelist-only parser.

## Architecture
```
browser tiles -> GET /puzzle, GET /solve?numbers=&target= -> api.py -> core.py (solve, evaluate, random_puzzle, solvable_share)
```

## Results
- The well-known hard example (100, 75, 50, 25, 6, 3 to reach 952) is solved exactly in about 0.26 s, searching 44,035 number sets: `((75 x 3) x (100 + 6) - 50) / 25`.
- 39 of 40 seeded random games (97.5%) are solvable exactly.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn countdown.api:app --port 8000
pytest
docker build -t countdown . && docker run -p 8000:8000 countdown
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Exhaustive search with memoisation on sorted number sets: a complete answer, and still fast for six numbers.
- Subtraction only when the result is positive and division only when exact: matches the game's rules and avoids duplicates.
- Closest value is returned when exact is impossible: the game rewards near misses.
- `evaluate` allows digits, operators and brackets only: the check never executes arbitrary text.

## Limitations
- Capped at six numbers between 1 and 100, and targets up to 999.
- Returns one expression, not the shortest or the most elegant.
- Pure Python; fine for six numbers, much slower beyond about eight.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. Puzzles are randomly generated.
