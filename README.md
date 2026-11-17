# Moon Phase Calendar

**Problem.** Anyone planning a night walk, a photo shoot, a garden task or a festival date wants to know the moon's phase. Simple apps use one fixed month length and drift by hours or even a day. How accurate can a small, dependency-free calculation be, and how do you *prove* it?

**Solution.** The moon's phase computed from astronomical formulas (Meeus, "Astronomical Algorithms"): mean month length plus the main corrections for the Sun's and Moon's uneven orbital speed. The page is a month calendar with a drawn moon, the percentage lit, an outline on full-moon days, and a measured accuracy panel comparing two models against 12 published full moons of 2024.

![demo](docs/demo.png)

**Measured result.** Against the 12 published 2024 full-moon times: mean month only, average error **6.87 hours** (worst 12.2); with the orbital corrections, average **0.17 hours (10 minutes)**, worst 0.36 hours (22 minutes). The tests fail if the corrected model drifts beyond 45 minutes.

## Data
`data/full_moons_2024.json`: the 12 published full-moon times of 2024 (UTC, to the minute), typed for this repo from public almanac tables. They are used only to test the model. The close agreement (all within 22 minutes of an independent calculation) also supports the values. Everything else is computed. MIT licence.

## Architecture
```
static/index.html (SVG moons) --GET /month?year=&month=, /accuracy--> api.py (FastAPI)
   core.phase_event_jd (mean + corrections) -> new / full moon times
   core._cycle (real new moons either side) -> age, illumination, phase name
   core.error_hours -> compare with data/full_moons_2024.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn moonphase.api:app --reload
pytest && ruff check .
docker build -t moonphase . && docker run -p 8000:8000 moonphase
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Published formulas, not a lookup table: works for any year 1900-2100 and each term can be explained.
- Test against real full moons, in hours: "looks right" is not a test, and the two-model comparison shows the corrections earn their place.
- Phase age from the actual new moons on each side: a fixed 29.53-day month is off by up to half a day for the same reason the mean model is.
- Julian dates internally: one number that makes date maths trivial and matches the astronomical tables.
- Drawn with SVG arcs from the computed percentage: no image assets and it scales on any screen.

## Limitations
Only the main correction terms are included (a full treatment has about 25), so times are good to about 20-30 minutes, not seconds; times are UTC, so the local date of a full moon can differ from the UTC date; illumination is a smooth curve through the new moons, so it is within about 8 percentage points of the true value at the quarters (first quarter shows 46% where the true value is 50%); only accuracy of full moons is tested, because that is the data I could cite; no moonrise or moonset, which depend on location.
