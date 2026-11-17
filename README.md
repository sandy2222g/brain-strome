# Swim Lane Assigner

**Problem.** A club session has more swimmers than lanes. Filling lanes in sign-up order puts a 68 s swimmer next to a 140 s one, so people overtake or block each other.

**Solution.** Sort swimmers by 100 m time and cut the line into lanes with dynamic programming so the summed fastest-to-slowest gap per lane is minimal, respecting a per-lane capacity.

![demo](docs/demo.png)

Sample (30 invented swimmers, 6 lanes, max 6 each): total spread **42.6 s** vs **292.6 s** in sign-up order (250 s saved).

## Architecture
```
static/index.html --POST /assign--> api.py (FastAPI) --> core.assign / signup_order
                                                          data/swimmers.json (invented)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn swimlane.api:app --reload
pytest && ruff check .
docker build -t swimlane . && docker run -p 8000:8000 swimlane
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Contiguous cuts of the sorted list: a lane never skips a slower swimmer, and it makes the problem exactly solvable.
- DP over (swimmers, lanes): optimal, and checked against brute force in tests.
- Sum of spreads as the objective: simple, explainable to a coach.
- Stateless API: no swimmer data is stored.

## Limitations
Uses one 100 m time per person (no stroke or age groups); lanes are balanced only through the capacity limit. Names and times are invented. MIT licence.
