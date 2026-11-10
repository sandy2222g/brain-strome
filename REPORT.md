# Report

Goal: build as many deployable, resume-ready open-source projects as time allows (stop 07:25 IST Nov 11; push by 07:30 IST).

## Progress log
- **Nov 10 21:28 IST** — Started. Repo `sandy2222g/brain-strome`, one branch per project from `main`. Env: Python 3.13, sandbox pip behind TLS proxy (slow, ~120 kB/s), Docker daemon had to be started manually (`dockerd`).
- **Project 1 chosen: support-ticket-triage** (customer support / NLP). Reason: universal real business problem, classic ML + FastAPI + UI, trains in seconds, fits free hosting.
- **21:55 IST** — Project 1 done: 20 tests pass, ruff clean, Docker image builds and serves /predict, README + DEPLOY + CI present.
- **Blocker (resolved):** `docker build` failed with `CERTIFICATE_VERIFY_FAILED` because the sandbox proxy re-terminates TLS. Fix: the Dockerfile accepts an optional BuildKit `cacert` secret; built locally with `--network host --secret id=cacert,...`. TLS verification was not disabled. Normal builds are unaffected.
