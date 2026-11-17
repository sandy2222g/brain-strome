# Elevator Dispatch Simulator

**Problem.** In a busy building, which lift-dispatch rule gets people moving fastest? Intuition ("serve whoever pressed first") turns out to be the worst for waiting time.

**Solution.** A discrete-event simulation of one lift (12 floors, 8 people, 2 s per floor, 5 s doors) replays the same 120-person morning rush under three policies: first-come-first-served, nearest-call-first and SCAN (sweep up, then down). It reports mean, 90th-percentile and maximum wait, plus ride time.

![demo](docs/demo.png)

**Measured result.** Mean wait: fcfs **201.8 s**, nearest **160.2 s**, scan **163.1 s**. Nearest wins on average wait but makes riders sit inside 44 s on average (fcfs 30 s, scan 32 s) because it detours for close calls. SCAN has the best 90th-percentile and maximum wait, so it is the fairest.

## Data
`data/arrivals.csv`: 120 synthetic trips (time, origin floor, destination floor) over about 12 minutes; 70% start in the lobby (floor 0) to mimic a morning rush. Generated for this repo; no real data. The load is deliberately heavy, so absolute waits are long; the ranking between policies is the point.

## Architecture
```
static/index.html --POST /compare--> api.py (FastAPI) --> core.simulate (event loop, 3 policies)
                                                          data/arrivals.csv
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn liftsim.api:app --reload
pytest && ruff check .
docker build -t liftsim . && docker run -p 8000:8000 liftsim
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Same arrivals for every policy: differences come from the rule, not luck.
- Floor-by-floor stepping: a lift passing a waiting person picks them up, as real lifts do.
- A full lift only heads for drop-offs: otherwise "nearest" ping-pongs between two waiting floors forever (found and fixed by a regression test).
- Report p90 and max wait as well as the mean: averages hide the unlucky rider.
- Pure Python and the standard library: the simulator is short enough to read in one sitting.

## Limitations
One lift, no destination-dispatch grouping, no door-hold or load-dependent speed, synthetic traffic only. MIT licence.
