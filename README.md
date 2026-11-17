# Golden Hour Planner

**Problem.** Photographers and hikers want to know when the light is best, but "sunrise at 6, sunset at 6" is wrong almost everywhere and apps need accounts or network calls.

**Solution.** Computes the sun's declination and equation of time with the NOAA low-precision formulas, then finds when the sun's elevation crosses key thresholds (-0.833°, 6°, -4°, -6°) for any latitude, longitude and date. It outputs sunrise, sunset, golden hour and blue hour, including polar day and a sunset just after midnight.

![demo](docs/demo.png)

**Measured accuracy.** Tests check four cities on 21 June 2026 against published times; all are within 2 minutes (London 04:43 / 21:22, New York 05:25 / 20:31, Mumbai 06:02 / 19:19, Sydney 07:00 / 16:54). A fixed 6:00–18:00 rule would be off by 77 and 202 minutes in London.

## Architecture
```
static/index.html --POST /plan--> api.py (FastAPI) --> core.plan: solar position -> elevation scan -> bisection
                                                         data/places.json (public coordinates)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn goldenhour.api:app --reload
pytest && ruff check .
docker build -t goldenhour . && docker run -p 8000:8000 goldenhour
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- NOAA formulas, no astronomy library: tiny dependency footprint and the maths is visible in one file.
- Scan every minute, then bisect each crossing: robust at high latitudes where closed-form hour-angle formulas break.
- 36-hour scan window: a sunset after midnight (Reykjavik in June) still attaches to the right day and is shown as "(+1)".
- Local time zone passed as a fixed offset: avoids a time-zone database, at the cost of no automatic daylight saving.
- Thresholds as named constants: golden hour (to 6°) and blue hour (-6° to -4°) are conventions, so they are easy to change.

## Limitations
Accurate to a minute or two, not for navigation; no terrain, weather or atmospheric variation; the user supplies the UTC offset. Place coordinates are public facts, rounded. MIT licence.
