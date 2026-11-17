# Pizza Order Planner

**Problem.** Ordering pizza for a mixed group (meat eaters, vegetarians, vegans) usually means over-buying or leaving someone with nothing.

**Solution.** Finds the cheapest order that gives every guest their slices from pizzas they can eat, while keeping a chosen share of the meat eaters' slices as real meat pizza.

![demo](docs/demo.png)

Sample (invented menu; 8 meat, 5 vegetarian, 3 vegan; 3 slices each; 60% meat): **$65.00** for 2 Pepperoni + 2 Margherita + 2 Veggie Supreme. The naive cheapest-per-slice order costs $54.00 but leaves 3 vegans with nothing to eat.

## Architecture
```
static/index.html --POST /plan--> api.py (FastAPI) --> core.cheapest / cheapest_slice_only
                                                        data/party.json (invented menu)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn pizzaplan.api:app --reload
pytest && ruff check .
docker build -t pizzaplan . && docker run -p 8000:8000 pizzaplan
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Nested diets (vegan ⊂ vegetarian ⊂ meat): feasibility reduces to three inequalities (Hall's condition), so the check is exact and instant.
- Exhaustive search over pizza counts: menus are small, and it is provably optimal (also tested against a second brute force).
- Prices in integer cents: no float rounding in totals.
- Stateless API: nothing about the party is stored.

## Limitations
Slices are interchangeable (no per-person toppings or allergies); the search is capped at 12 of each pizza and 8 menu items. Menu and prices are invented. MIT licence.
