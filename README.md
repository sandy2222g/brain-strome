# Bake Sale Pricer

![demo](docs/demo.png)

## Problem
You sell brownies, loaves and cupcakes and have tried different prices. What should each cost to make the most profit?

## Solution
Fit a constant-elasticity demand curve, units = a * price^e, by least squares on logs for each item. If e is below -1 the profit-maximising price is cost * e / (1 + e). If e is -1 or above, profit keeps rising, so the price goes to the top of the range you tried. Prices never leave the tried range.

On 12 invented weeks for five bakes (data from `scripts/make_data.py`, hidden true elasticities used only to check the answer):

| | Fitted vs true elasticity | Profit vs "double the cost" |
|---|---|---|
| Brownie | -1.74 vs -1.8 | +1% |
| Sourdough loaf | -1.28 vs -1.3 | +22% |
| Cupcake | -2.43 vs -2.4 | +3% |
| Cookie | -1.61 vs -1.6 | +5% |
| Millionaire shortbread | -1.17 vs -1.2 | +34% |
| **All five** | | **+10.6%** under the true demand ($1,252 vs $1,132 a week) |

## Architecture
```
data/sales.csv or POST body -> core.fit (log-log least squares) -> core.best_price / cost_plus_price
                            -> FastAPI /price -> static/index.html (demand curve, observed points, price markers)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn bakeprice.api:app --port 8000
pytest -q && ruff check .
docker build -t bakeprice . && docker run -p 8000:8000 bakeprice
```
Endpoints: `GET /health`, `GET /sample`, `POST /price`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Constant-elasticity model: two parameters fit from a dozen points, and the optimum has a closed form.
- Fit on logs: the power law becomes a straight line, so least squares is exact and needs no libraries.
- Answer clamped to the tried price range: the data says nothing outside it, so the tool refuses to extrapolate.
- Baseline is cost plus 100%: a common rule of thumb that needs no data.
- Hidden truth kept out of the app: it is used only by tests to score the recommendation honestly.

## Limitations
- Data is synthetic and generated from the same model family, so the fit is easier than real sales.
- One price per item; no day-of-week effects, competitors or stock limits.
- The UI percentage uses the fitted curves; the table above uses the true demand, which is the honest number.
- Unit costs and sales are invented (MIT).
