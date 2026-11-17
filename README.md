# Cafe Demand Forecaster

**Problem.** A small cafe bakes pastries every morning. Too few means lost sales, too many means waste. Weekends are much busier than weekdays, and sales drift upward, so "same as yesterday" is wrong.

**Solution.** Additive Holt-Winters exponential smoothing (level + trend + weekly season), written from scratch. Smoothing parameters are chosen by a grid search on one-step-ahead error. The bake quantity adds a safety margin of 1.28 standard deviations of that error, giving roughly a 90% chance of covering demand.

![demo](docs/demo.png)

**Measured result.** Holding out the last 14 days of the synthetic sales history: mean absolute error **7.41** items for Holt-Winters vs **10.07** for "same weekday last week" (26% lower).

## Data
`data/sales.csv`: 98 days of synthetic daily sales, generated for this repo as 60 + 0.15·day + a weekday effect (Saturday +25) + noise (σ = 5). No real business data. Because the generator is exactly the kind of pattern Holt-Winters models, real shops will see smaller gains.

## Architecture
```
static/index.html --GET /evaluation, POST /plan--> api.py (FastAPI)
                                                   --> core.fit (grid search) -> core.forecast / plan_bakes
                                                   data/sales.csv (synthetic)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn cafecast.api:app --reload
pytest && ruff check .
docker build -t cafecast . && docker run -p 8000:8000 cafecast
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Holt-Winters, not a neural net: three weeks of data is enough, and the three parameters are interpretable.
- Additive seasonality: weekday differences are roughly constant in size, not proportional.
- Grid search over 64 parameter triples: small, deterministic, no optimiser dependency.
- Safety stock from residual sigma: ties the bake quantity to how predictable the shop actually is.
- Seasonal-naive baseline and a fixed 14-day holdout: the improvement is measured, not asserted.

## Limitations
No holidays, weather or promotions; at least 3 weeks of history are needed; errors are assumed to be roughly normal; stock-outs hide true demand (sales are not the same as demand). MIT licence.
