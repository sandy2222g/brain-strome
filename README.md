# Weekly Menu Planner

![demo](docs/demo.png)

## Problem
Planning seven dinners by hand ends with chicken three times, a 90-minute roast on a Tuesday, or the same dish twice.

## Solution
A backtracking search assigns one dish per day under three rules: no dish repeats, the same protein never appears on consecutive days, and weeknight dishes take at most 30 minutes (weekends are unrestricted). Sample (invented dishes): Mon chicken stir-fry, Tue egg fried rice, Wed fish tacos, Thu lentil dal, Fri salmon bake, Sat beef chilli, Sun chicken curry. Taking the first seven dishes in list order breaks 3 rules (a 45-minute Monday, chicken two days running, a 60-minute Thursday).

## Architecture
```mermaid
flowchart LR
  UI[static page] -->|POST /plan| API[FastAPI api.py]
  API --> Core[core.py: plan, violations]
  Core --> Data[data/dishes.json]
```

## Setup
```bash
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn menuplan.api:app --port 8000
PYTHONPATH=src pytest
docker build -t menuplan . && docker run -p 8000:8000 menuplan
```
Deploy: see [DEPLOY.md](DEPLOY.md) (Render or Hugging Face Spaces).

## Design decisions
- Backtracking search: a greedy pick can dead-end late in the week, backtracking finds a plan whenever one exists.
- Dishes tried in name order: the same input always gives the same plan.
- Rules checked by a separate `violations` function: the baseline's failures are shown, not just claimed.
- Clear error when no plan exists: better than a silently broken week.

## Limitations
- Returns the first valid plan, not the "best" one (no taste or cost scoring).
- Worst-case search is exponential, fine for seven days and a few dozen dishes.
- Dishes are invented; no nutrition data.

Data: invented, MIT licence.
