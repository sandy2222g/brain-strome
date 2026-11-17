# Debt Payoff Strategist

**Problem.** With several debts and one monthly budget, which should you pay first? People guess and overpay interest.

**Solution.** Simulates month by month, in integer cents, three plans: *avalanche* (highest APR first), *snowball* (smallest balance first) and *minimums only*. Rolls freed-up payments forward and reports months, total interest and payoff order.

![demo](docs/demo.png)

Sample (invented data, budget 600): avalanche 27 months / 1940.87 interest; snowball 27 / 2018.52; minimums only 70 / 5221.86.

## Architecture
```
static/index.html --POST /compare--> api.py (FastAPI) --> core.simulate/compare
                                                           data/debts.json (sample)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn debtplan.api:app --reload
pytest && ruff check .
docker build -t debtplan . && docker run -p 8000:8000 debtplan
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Integer cents: avoids float drift in long simulations.
- Avalanche tested against every payoff permutation: proves it is the cheapest order.
- Stateless API: nothing about your debts is stored.
- Cap at 600 months: stops hopeless inputs from looping forever.

## Limitations
Fixed APRs, monthly compounding, no fees or new borrowing; snowball ignores the motivation benefit. Not financial advice. Data is invented. MIT licence.
