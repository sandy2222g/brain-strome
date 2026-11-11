# League Fixture Planner

![demo](docs/demo.png)

## Problem
A local league needs a round-robin schedule where every team plays every other once. Done carelessly, one team is always at home and another never is, or a team plays three home games in a row.

## Solution
The circle method fixes one team and rotates the rest to form the rounds, and home/away is alternated so each team's pattern flips as often as possible. A "break" is a team playing home (or away) twice in a row; for n teams (n even) at least n - 2 breaks are unavoidable, and this schedule reaches that. On the sample league (8 teams, 7 rounds):

| | Breaks | Home games per team |
|---|---|---|
| Naive: first-listed team always home | 30 | 0 to 7 |
| Balanced circle method | **6** (the minimum, n - 2) | 3 or 4 |

An odd number of teams adds a "BYE" team so one team rests each round.

## Architecture
```
data/league.json or POST body -> core.build (validate) -> core.circle_schedule / core.naive_schedule
                              -> core.count_breaks, core.home_counts -> FastAPI /schedule -> static/index.html
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn fixtures.api:app --port 8000
pytest -q && ruff check .
docker build -t fixtures . && docker run -p 8000:8000 fixtures
```
Endpoints: `GET /health`, `GET /sample`, `POST /schedule`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Circle method: a standard construction that guarantees every pair meets exactly once in n - 1 rounds.
- Alternating home and away: reaches the proven minimum number of breaks, which a test checks for several team counts.
- Naive baseline kept in the output: it shows how unfair "listed first is home" really is.
- BYE slot for odd leagues: keeps the construction unchanged and drops the bye games afterwards.
- Cap of 24 teams: keeps the page readable.

## Limitations
- Single round-robin only; no second half-season, venues, or "no clash with other leagues" rules.
- Home/away balance is per team across the season; it does not weigh travel distance.
- Team names are invented (MIT).
