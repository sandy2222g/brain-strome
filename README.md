# Exam Runway

![CI](https://github.com/sandy2222g/brain-strome/actions/workflows/ci.yml/badge.svg?branch=exam-runway)

Plan your revision day by day. Exam Runway schedules short reviews that space out as you learn, and shows how much you will remember on exam day and for how long after.

![Demo](docs/demo.png)

## Problem
Students cram. The night before feels productive, but recall fades within days. Spaced repetition fixes that, yet most planners just split hours evenly across topics and ignore how memory works.

## Solution
You enter topics (share of marks, difficulty, how well you know them), an exam date, daily hours and rest days. The planner simulates every day up to the exam:
- a **forgetting-curve model** tracks how well each topic is remembered,
- each day it studies what is **most forgotten, most valuable and hardest** first, within your hour budget,
- every review **grows the topic's memory stability**, so gaps between reviews expand on their own,
- a small **score model** (ridge regression on synthetic study-habit data) turns the plan's total hours, spacing, difficulty, confidence and sleep into an expected score,
- warnings tell you when a topic will be weak or the window is too short.

## Architecture
```mermaid
flowchart LR
  F[Form in static/index.html] -->|POST /plan| API[FastAPI]
  API --> P[planner.build_plan<br/>day-by-day greedy simulation]
  P --> M[memory.py<br/>R=exp(-t/S), review gain]
  API --> S[predictor.ScoreModel<br/>Ridge on study habits]
  G[scripts/generate_data.py] --> D[(data/study_sessions.csv)] --> T[runway.train] --> S
```
```
src/runway/  memory.py (forgetting curve) · planner.py (schedule) · predictor.py (score model) · api.py · train.py
tests/       23 tests: memory maths, planner invariants, score model, API
```

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=src python -m runway.train
PYTHONPATH=src uvicorn runway.api:app --reload      # http://localhost:8000, docs at /docs
pytest -q && ruff check .
```
Docker: `docker build -t exam-runway . && docker run --rm -p 8000:8000 exam-runway`. Deploy: [DEPLOY.md](DEPLOY.md).

## Design decisions
- **Exponential forgetting curve with a per-topic stability** — the simplest model with the right behaviour: recall decays, reviews help most when you have forgotten more.
- **Greedy day-by-day simulation, not an optimiser** — transparent, deterministic, easy to test; each day's choice can be explained in one sentence.
- **Always allow a review in the last 3 days** — found by a failing test: skipping "still fresh" topics left stale material on exam day with more study time.
- **Report recall half-life as well as recall on exam day** — recall right after a review is always high; half-life shows whether the plan builds durable memory, which is what separates spacing from cramming (covered by a test).
- **Score model is separate from the planner** — the plan stays rule-based and explainable; the regression only adds an estimate and has its own metrics (MAE 3.1 vs 10.0 baseline on held-out synthetic data).
- **Synthetic study data with a built-in "cramming hurts" effect** — no real student records; documented so the model is not mistaken for evidence.
- **Visual system dealt with the taste-skill kit** (palette "cool-grey-cobalt", IBM Plex Sans/Mono); boarding-pass cards because the tool is about a date you must arrive at ready.
- **Plain HTML/CSS/JS with no build step** — nothing to install, readable in a minute.

## Dataset
`data/study_sessions.csv`: 1,500 synthetic rows from `scripts/generate_data.py` (seed 11). No real students; CC0.

## Limitations
- The memory model uses one curve shape for everyone; real memory varies by person and material.
- The score model learns from synthetic data, so it demonstrates the method, not real-world accuracy.
- No calendar import, and every topic is treated as independent (no prerequisites).
- Hours are planned, not tracked; the plan does not re-adapt when you miss a day (re-run it from today).

## License
MIT.
