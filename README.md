# A/B Test Judge

A small A/B testing toolkit: is version B really better, how much traffic do you need, and why checking early misleads.

![demo](docs/demo.png)

## Problem
Teams ship changes because "B converted better", often on noise. Reliable decisions need a significance test, a planned sample size, and discipline about peeking.

## Solution
A FastAPI service and page with three tools, all implemented from first principles with the standard library:
1. Two-proportion z-test (pooled variance) with p-value and a 95% confidence interval for the lift.
2. Sample size per version for a chosen base rate and minimum lift (80% power, 5% alpha).
3. A simulation of the peeking trap: two identical versions, tested repeatedly, to show the inflated false-positive rate.

## Architecture
```
browser -> POST /analyse, GET /sample-size, GET /peeking -> api.py -> core.py (analyse, sample_size, false_positive_rate)
```

## Results
- 200/2000 vs 250/2000: z = 2.50, p = 0.0124, lift between 0.5 and 4.5 points (checked by hand in the tests).
- Detecting +2 points on a 10% base rate needs 3,841 visitors per version; detecting +1 point needs 14,751 (about 3.8x as many).
- Peeking on identical versions (200 visitors per version between looks): 1 look is wrong about 5% of the time, 5 looks about 15%, 10 looks about 21%.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn abjudge.api:app --port 8000
pytest
docker build -t abjudge . && docker run -p 8000:8000 abjudge
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Standard library only (`statistics.NormalDist`): fewer dependencies and every formula visible.
- Pooled variance for the test, unpooled for the interval: the textbook choice for each purpose.
- Report the interval, not just the p-value: it shows the range of plausible lifts.
- Peeking simulation cached on first request: it takes a few seconds and never changes.

## Limitations
- Conversion rates only (two groups); no continuous metrics, multiple variants or Bayesian analysis.
- The normal approximation is poor for very small counts.
- Sequential testing corrections (alpha spending) are not implemented; the app only demonstrates the problem.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. All data is user input or simulated.
