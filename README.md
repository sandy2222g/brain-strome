# Bill Timing Planner

![demo](docs/demo.png)

## Problem
Income and bills arrive on different days, so a month can look fine in total yet overdraw the account for days: the rent is due on the 1st and payday is on the 5th.

## Solution
Simulate the balance day by day, list every overdrawn day, then suggest the smallest set of due-date moves to the next payday that clears them. Sample (invented month, opening balance 150): the balance is below zero on 9 days (lowest -585). Moving Rent from day 1 to day 5 and Insurance from day 12 to day 19 removes every shortfall without changing the month's total.

## Architecture
```mermaid
flowchart LR
  UI[static page + SVG chart] -->|POST /check| API[FastAPI api.py]
  API --> Core[core.py: balances, shortfalls, suggest_moves]
  Core --> Data[data/month.json]
```

## Setup
```bash
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn billtime.api:app --port 8000
PYTHONPATH=src pytest
docker build -t billtime . && docker run -p 8000:8000 billtime
```
Deploy: see [DEPLOY.md](DEPLOY.md) (Render or Hugging Face Spaces).

## Design decisions
- Daily simulation: simple, exact and easy to check by hand.
- Greedy fix (delay the largest bill to the next payday): a person can do it in real life and it is explainable, but not proven optimal.
- Moves limited to 7 days: most billers allow a short change of due date, not more.
- Money as floats rounded to cents: fine for a planner; a ledger would use integer cents.
- Invented figures, nothing stored: no real accounts involved.

## Limitations
- Ignores overdraft fees, interest and late-payment fines.
- Suggestions may not be possible with your real billers.
- Greedy: it can miss a better combination of moves.

Data: invented, MIT licence.
