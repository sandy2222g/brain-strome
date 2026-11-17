# Tournament Bracket Maker

**Problem.** Anyone running a league or a office tournament must choose a format: a knockout (fast, but one bad day ends a season) or a round robin (fair, but long). In a knockout, how the draw is made decides whether the two best teams meet in the final or knock each other out in round one.

**Solution.** The standard seeded bracket (1 plays the lowest seed, 1 and 2 can only meet in the final, byes go to the top seeds), the circle-method round-robin schedule, and a Monte Carlo simulation (4,000 tournaments) that measures how often the best team actually wins under each format. Pick 4-12 teams and see the draw, the schedule size and the title chances.

![demo](docs/demo.png)

**Measured result (12 invented teams, ratings 980-1420).** Chance the strongest team wins the title: random-draw knockout 31.3%, **seeded knockout 36.9%**, **round robin 40.8%**. Seeding is worth about 5.6 points of fairness for free; a round robin adds about 4 more at the cost of 66 games instead of 11. Tests assert this ordering on a fixed random seed.

## Data
`data/teams.json`: 12 invented teams with made-up ratings (an office five-a-side league), written for this repo (MIT). Win chances use the Elo formula: a 400-point rating gap means about a 10-to-1 favourite.

## Architecture
```
static/index.html --GET /bracket?n=, /simulate?n=&trials=--> api.py (FastAPI)
   core.seed_order -> core.first_round (byes to top seeds) -> core.run_knockout
   core.round_robin (circle method) -> core.run_round_robin
   core.simulate: seeded vs random draw vs round robin, same random generator
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn bracketmaker.api:app --reload
pytest && ruff check .
docker build -t bracketmaker . && docker run -p 8000:8000 bracketmaker
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Standard doubling construction for seed order: it guarantees opposite halves for seeds 1 and 2 and is easy to prove (tests check every round's pairs sum to size + 1).
- Byes always go to the top seeds: rewards the regular season and is how real brackets work.
- Elo win probability: one number per team is enough to demonstrate the effect, and it is the standard rating model.
- Circle method for the round robin: every pair meets exactly once and nobody plays twice in a round (both tested up to 12 teams).
- Same simulation for all three formats with one random generator: differences are caused by the format, not by luck.
- Results cached per team count and trial count: the page can be re-opened instantly.

## Limitations
Single-elimination only (no double elimination, groups or playoffs after a round robin); ratings are fixed and made up, with no home advantage, injuries or draws; the round-robin winner is the team with most wins and ties are broken by coin flip rather than head-to-head; simulation noise is about +/-0.7 percentage points at 4,000 trials; the draw is shown for round one only.
