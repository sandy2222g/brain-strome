# Kitchen Stock Reorder

**Problem.** A small kitchen either runs out of milk on a busy Saturday or throws away a crate of tomatoes. Ordering "about what we used last week" ignores two things: how much demand varies day to day, and how long a delivery takes.

**Solution.** For each ingredient the planner learns average daily demand and its variability from history, then sets a **reorder point** (expected use during the delivery lead time plus a safety stock for a chosen service level) and a **top-up level** capped by shelf life. It is tested by replaying 30 unseen days day by day, with first-in-first-out stock that expires, against the common habit of ordering last week's total every Monday.

![demo](docs/demo.png)

**Measured result.** Over 30 held-out days x 5 ingredients at a 95% service level, the reorder-point policy has **2** empty-shelf days vs **9** for the weekly order, and throws away **$103** of stock vs **$618**, while holding 36-65% less stock. At 99% it has no empty-shelf days at all.

## Data
`data/ingredients.csv` (shelf life, delivery lead time, unit cost) and `data/demand.csv` (120 days of daily units for five ingredients): synthetic, generated for this repo with a weekday pattern (weekend peak) plus noise. No real kitchen data. The first 90 days are used to plan, the last 30 to test.

## Architecture
```
static/index.html --GET /evaluation?service=--> api.py (FastAPI) --> core.plan     (mean, sd, z, reorder point, cap)
                                                                    --> core.simulate (FIFO batches, lead times, expiry)
                                                                    data/ingredients.csv, data/demand.csv
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn stockwise.api:app --reload
pytest && ruff check .
docker build -t stockwise . && docker run -p 8000:8000 stockwise
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Safety stock = z x sd x sqrt(cover days): demand noise adds up like a random walk, not linearly.
- Cover = lead time + 1 day: an order placed at end of day lands lead + 1 days later. The first version used the lead time alone and missed its 95% target on milk and tomatoes; fixing it cut shortages from 13 to 2.
- Cap at 80% of a shelf life of average demand: stops the policy from over-ordering perishables.
- z from bisection on the normal CDF: no scipy for one function.
- Plan on the first 90 days, test on the last 30: the policy never sees the demand it is judged on.

## Limitations
Assumes demand is roughly stationary and independent day to day (no promotions, holidays or weather); one supplier, no minimum order quantities or price breaks; the weekly baseline is a simple habit, not an optimised schedule; synthetic data, so absolute dollar figures are illustrative. MIT licence.
