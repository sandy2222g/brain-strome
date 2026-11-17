# Chase Win Estimator

**Problem.** In a limited-overs cricket chase, "required rate 9.5, current rate 7.7" only says *behind*. It ignores wickets in hand and does not say how likely a win actually is.

**Solution.** A dynamic programme over (balls left, wickets lost, runs needed) gives the **exact** probability that the chasing side wins, from per-ball outcome probabilities (dot, 1, 2, 3, 4, 6, wicket, wide/no-ball). Three batting-style presets show how the odds shift.

![demo](docs/demo.png)

Sample (target 168, 92/4, 48 balls left, balanced style): **18.9%** to win (61.5% if the batters attack, 0.2% if they play defensively). The run-rate rule of thumb only says "behind".

The DP is cross-checked by a 40,000-run Monte Carlo simulation (difference below 1.2 points) and by hand-computed one-ball cases.

## Architecture
```
static/index.html --POST /estimate--> api.py (FastAPI) --> core.win_probability (DP) / run_rate_baseline
                                                            data/presets.json (invented per-ball models)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn chasewin.api:app --reload
pytest && ruff check .
docker build -t chasewin . && docker run -p 8000:8000 chasewin
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- DP, not simulation: exact answer, repeatable, and fast (under a second for a full 50-over chase).
- Extras advance the score but not the ball: the recurrence stays on the same ball layer, which keeps the maths faithful to the rules.
- Per-ball probabilities as explicit presets: assumptions are visible and editable in `data/presets.json`.
- Monte Carlo kept in the code as a test oracle: an independent check of the DP.
- Input limits (300 balls, 300 runs needed): keeps the free-tier server responsive.

## Limitations
Every ball is independent and identical: no batter quality, bowler type, pitch, powerplay or death-over effects; no leg-byes, run-outs or free hits; probabilities are invented, not fitted to real matches. MIT licence.
