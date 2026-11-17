# Cron Explainer

**Problem.** `*/15 9-17 * * 1-5` is a schedule almost nobody can read at a glance, and cron fails silently: a wrong field means a job that runs at 3 a.m. on the wrong day or never runs at all.

**Solution.** A from-scratch parser for standard five-field cron expressions (lists, ranges, steps, month and weekday names, the `@daily`-style macros) that explains the schedule in plain English and calculates the next run times by walking the calendar. Invalid fields get specific messages ("hour: 25 is outside 0-23"). The page has five editable fields, example chips and the upcoming runs.

![demo](docs/demo.png)

**Measured result.** 10 tests cover parsing, the English wording, the classic "day of month OR weekday" rule (`0 9 15 * 1` runs on the 15th *and* on every Monday), leap-day schedules (`0 0 29 2 *` next runs 2028-02-29, then 2032-02-29), impossible dates (`0 0 31 2 *` never runs) and eight kinds of invalid input. Expected run times were worked out by hand against a calendar.

## Data
`data/examples.json`: eight example schedules with labels (written for this repo). No other data; the "now" for the demo is fixed at 2026-11-17 12:00 so results are reproducible.

## Architecture
```
static/index.html --GET /explain?expr=&n=&start=, /examples--> api.py (FastAPI)
                                                              --> core.parse (field sets) -> core.next_runs (day-by-day walk)
                                                              --> core.explain (English wording)
                                                              data/examples.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn cronexplain.api:app --reload
pytest && ruff check .
docker build -t cronexplain . && docker run -p 8000:8000 cronexplain
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Each field expands to a set of allowed numbers: matching a time is then four set lookups, no string handling.
- Walk day by day and pick hours and minutes from sorted sets: fast enough (at most 8 years of days) and obviously correct, unlike clever date arithmetic.
- Day-of-month and weekday combine with OR when both are restricted: that is how classic cron behaves and the most common surprise for newcomers, so it is tested and explained in the page.
- Strictly after the start time: a job that "runs now" is not an upcoming run.
- Specific error messages naming the field: "minute: 61 is outside 0-59" saves a trip to the manual.

## Limitations
Five-field Unix cron only (no seconds field, `L`, `W`, `#` or `?` extensions); no time zones or daylight-saving handling (times are naive local times); English wording is simplest for common patterns and verbose for unusual ones; times beyond 8 years return nothing. MIT licence.
