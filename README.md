# Elo Rating League

**Problem.** A club (table tennis, chess, darts) wants a ranking, but not everyone plays everyone. Ranking by win rate rewards beating weak opponents and punishes playing strong ones, so the league table misleads whenever the schedule is lopsided.

**Solution.** Elo ratings update after every match: beating a stronger player earns more points than beating a weaker one, and points only move between the two players. The app shows a live leaderboard with each player's rating history, and predicts the winner of any pairing from the rating gap.

![demo](docs/demo.png)

**Measured result.** On 240 synthetic matches where two sub-clubs mostly play within themselves (15% cross-club games), Elo trained on the first 180 matches ranks players closer to their hidden true skill than win rate does (Spearman **0.877** vs **0.775**) and predicts the winner of the next 60 games **73%** vs **68%** of the time. With only 60 test games the accuracy gap is within noise; the ranking gap is the more reliable signal.

## Data
`data/matches.csv`: 240 synthetic matches between 12 invented players in two sub-clubs, generated for this repo from hidden true ratings (`data/truth.json`, used only for evaluation) with a logistic win model. No real people or matches.

## Architecture
```
static/index.html --GET /leaderboard, /predict, /evaluation--> api.py (FastAPI)
                                                               --> core.rate (sequential Elo, K=24, start 1000)
                                                               --> core.win_rates, core.spearman, core.evaluate
                                                               data/matches.csv, data/truth.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn eloleague.api:app --reload
pytest && ruff check .
docker build -t eloleague . && docker run -p 8000:8000 eloleague
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Sequential updates in match order: ratings track form, and a new player starts moving immediately.
- K = 24 and a start of 1000: common club defaults, fast enough to settle in a season of about 20 games each.
- Zero-sum updates: total rating stays constant, which a test checks.
- Evaluate on later matches only: predicting games the model has already seen would flatter both methods.
- Compare against win rate, and against hidden skill: ranking quality is measured, not asserted.

## Limitations
Single K for everyone (no provisional ratings for newcomers); no draws, home advantage or margin of victory; ratings of players who never meet across sub-clubs rely on a few bridge matches; synthetic data. MIT licence.
