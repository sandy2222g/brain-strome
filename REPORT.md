# Report

Goal: build as many deployable, resume-ready open-source projects as time allows (stop 07:25 IST Nov 11; push by 07:30 IST).

## Progress log
- **Nov 10 21:28 IST** — Started. Repo `sandy2222g/brain-strome`, one branch per project from `main`. Env: Python 3.13, sandbox pip behind TLS proxy (slow, ~120 kB/s), Docker daemon had to be started manually (`dockerd`).
- **Project 1 chosen: support-ticket-triage** (customer support / NLP). Reason: universal real business problem, classic ML + FastAPI + UI, trains in seconds, fits free hosting.
- **21:55 IST** — Project 1 done: 20 tests pass, ruff clean, Docker image builds and serves /predict, README + DEPLOY + CI present.
- **Blocker (resolved):** `docker build` failed with `CERTIFICATE_VERIFY_FAILED` because the sandbox proxy re-terminates TLS. Fix: the Dockerfile accepts an optional BuildKit `cacert` secret; built locally with `--network host --secret id=cacert,...`. TLS verification was not disabled. Normal builds are unaffected.
- **22:20 IST — user feedback received mid-run:** wants unique, everyday, non-technical-domain projects (not support-ticket/bug/sensor style) and allowed up to 2 agents in parallel. Project 3 redirected to a food-waste app; later projects will follow that style.
- **Project 2 chosen: clinic-noshow-predictor** (healthcare operations). Reason: real cost problem, tabular ML with calibration + fairness audit, different domain from project 1. Decision: isotonic calibration produced hard 0/1 probabilities, switched to sigmoid. 14 tests pass, ruff clean, Docker builds and serves.
- **22:50 IST — user feedback:** use only 1 agent at a time; use the "taste-skill" (github.com/Leonxlnx/taste-skill, cloned to /tmp) for visual identity so projects do not look alike; each project is its own branch.
- **Project 4 chosen: exam-runway** (student study planning). Reason: unique, relatable to non-technical users; combines a forgetting-curve simulation with a score regression. Palette cool-grey-cobalt + IBM Plex dealt by taste-skill. Found by a test: skipping reviews near the exam gave worse readiness with more study time, fixed with a final-review window; added recall half-life as a metric that separates spacing from cramming. 23 tests, ruff clean, Docker builds and serves.
