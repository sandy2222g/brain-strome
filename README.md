# Transit Pass Chooser

![demo](docs/demo.png)

## Problem
A bus service sells single fares, day passes, week passes, a monthly pass and a weekly fare cap. Which one is cheapest depends on how often you actually ride.

## Solution
Give it four weeks of daily ride counts and it costs every option exactly, then picks the cheapest (ties go to the simpler option). On the 5 sample riders (invented fares, single $2.75, week pass $22, month pass $80):

| Rider | Rides | Best | Cost | Singles would cost |
|---|---|---|---|---|
| Occasional shopper | 16 | single | $44.00 | $44.00 |
| Part-time student | 34 | month pass | $80.00 | $93.50 |
| Daily commuter | 42 | month pass | $80.00 | $115.50 |
| Errand runner | 44 | month pass | $80.00 | $148.50 |
| Weekend explorer | 42 | day pass | $42.00 | $115.50 |

A week pass only beats singles above 8 rides a week (22 / 2.75).

## Architecture
```mermaid
flowchart LR
  UI[static page] -->|POST /choose| API[FastAPI api.py]
  API --> Core[core.py: cost per option, best_option]
  Core --> Data[data/riders.json]
```

## Setup
```bash
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn farepass.api:app --port 8000
PYTHONPATH=src pytest
docker build -t farepass . && docker run -p 8000:8000 farepass
```
Deploy: see [DEPLOY.md](DEPLOY.md) (Render or Hugging Face Spaces).

## Design decisions
- Exact costing of every option: there are only five, so no heuristic is needed.
- Day pass applied per day as min(rides x single, pass): it is what a rider would do in practice.
- Ties go to the earlier, simpler option: fewer things to buy and remember.
- Stateless API with synthetic data: nothing personal is stored.

## Limitations
- Assumes the next month looks like the logged one; real riding varies.
- Passes are costed on calendar-aligned weeks; pass validity windows, transfers and zones are not modelled.
- Fares are invented, not any real operator's.

Data: invented, MIT licence.
