# Meal Prep Mixer

![demo](docs/demo.png)

## Problem
Eating on a budget: you need enough calories and protein, and the cheapest calories (rice, oats) are low in protein. What is the cheapest daily set of servings that still hits both?

## Solution
The classic diet problem, solved exactly: try every combination of 0 to 4 servings of nine foods (pruned by cost) and keep the cheapest one inside the calorie range with enough protein. Targets on the sample: 2,000 to 2,300 kcal and at least 110 g protein.

| | Cost / day | Calories | Protein | Targets met |
|---|---|---|---|---|
| Cheapest per calorie first | $3.55 | 2,110 | 90 g | **No (20 g short)** |
| Best mix (exact) | $3.90 | 2,105 | 110 g | Yes |

The baseline is cheaper only because it ignores protein; hitting protein costs 35 cents a day more.

## Architecture
```
data/foods.json or POST body -> core.build (validate) -> core.best_mix (branch and bound) / core.cheapest_per_kcal
                             -> FastAPI /mix -> static/index.html (two receipts)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn mealmix.api:app --port 8000
pytest -q && ruff check .
docker build -t mealmix . && docker run -p 8000:8000 mealmix
```
Endpoints: `GET /health`, `GET /sample`, `POST /mix`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Exact search instead of an LP library: 9 foods and a serving cap keep it to milliseconds, with no dependencies.
- Cost pruning: any partial mix already as expensive as the best found is dropped.
- Integer servings: you cannot buy 1.37 servings of tofu.
- Baseline fails the target on purpose: it shows what cheap-calorie shopping really does to protein.
- Clear 422 for impossible targets: the API says so rather than returning a near miss.

## Limitations
- Only calories and protein; no fibre, fat, variety or allergies.
- Nutrition values and prices are rounded, invented numbers (MIT), not advice.
- Capped at 9 foods and 8 servings each.
