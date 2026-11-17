# Final Grade Needed

**Problem.** Students know their scores so far but not what the final exam must be worth for an A or a B, especially with weighted categories and "drop the lowest quiz" rules.

**Solution.** Applies each category's drop-lowest rule, weights the results, and solves for the average needed on the ungraded categories to reach every grade band. It flags each band as secured, possible or impossible.

![demo](docs/demo.png)

Sample (invented course, 75% graded): standing 84.98%; A needs 105.05% (impossible), B needs 65.05%, C 25.05%, D secured. A plain average of all scores would claim 78.08%, which ignores weights and dropped scores.

## Architecture
```
static/index.html --POST /analyse--> api.py (FastAPI) --> core.analyse / naive_mean
                                                           data/course.json (invented)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn gradeneed.api:app --reload
pytest && ruff check .
docker build -t gradeneed . && docker run -p 8000:8000 gradeneed
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Closed-form solve for the needed score: it is exact and instant, with no search.
- Test feeds the needed score back in and checks it lands on the band: proves the formula, not just the arithmetic.
- Never drop a category's last score: avoids a category silently becoming empty.
- Weights must total 100: rejects typos instead of guessing.
- Stateless API: grades are not stored.

## Limitations
No curves, extra credit, minimum-pass rules or rounding policies; the same average is assumed across all ungraded categories. Course data is invented. MIT licence.
