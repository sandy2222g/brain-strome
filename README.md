# Coupon Stack Chooser

**Problem.** Checkout pages accept several coupons, but only some combine: groups are exclusive, minimum spends apply, and percentage caps change the order of value. Most people just pick the biggest percentage.

**Solution.** Enumerates every coupon subset (at most 2^14), drops the ones that break a group or minimum-spend rule, prices each in integer cents, and returns the cheapest checkout. The receipt shows each discount step.

![demo](docs/demo.png)

Sample (invented cart, $120 + $8 shipping, 7 coupons): best stack SAVE20 + WELCOME15 + LOYAL8 + FIVEOFF + FREESHIP gives **$70.07** (saves $57.93). The biggest-percentage-only habit pays $104.00, i.e. $33.93 more.

## Architecture
```
static/index.html --POST /choose--> api.py (FastAPI) --> core.best (subset search) / best_single_percent
                                                          data/cart.json (invented)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn couponstack.api:app --reload
pytest && ruff check .
docker build -t couponstack . && docker run -p 8000:8000 couponstack
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Exhaustive subset search: coupon lists are short and the caps make the problem non-greedy, so brute force is the simplest provably correct choice.
- Fixed order (percent, then fixed, then shipping): stores differ, so one documented order is better than a guess.
- Integer cents with half-up rounding: totals match a receipt to the cent.
- Hard limit of 14 coupons: keeps worst-case work bounded for a public API.
- Ties prefer fewer coupons: simpler checkout when the total is equal.

## Limitations
Real stores have their own stacking and rounding rules, so adjust the order in `total_with` to match one; no per-item coupons or category exclusions; the coupon codes are invented. MIT licence.
