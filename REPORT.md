# Report

Goal: build as many deployable, resume-ready open-source projects as time allows (stop 07:25 IST Nov 11; push by 07:30 IST).

## Progress log
- **Nov 10 21:28 IST** — Started. Repo `sandy2222g/brain-strome`, one branch per project from `main`. Env: Python 3.13, sandbox pip behind TLS proxy (slow, ~120 kB/s), Docker daemon had to be started manually (`dockerd`).
- **Project 1 chosen: support-ticket-triage** (customer support / NLP). Reason: universal real business problem, classic ML + FastAPI + UI, trains in seconds, fits free hosting.
- **21:55 IST** — Project 1 done: 20 tests pass, ruff clean, Docker image builds and serves /predict, README + DEPLOY + CI present.
- **Blocker (resolved):** `docker build` failed with `CERTIFICATE_VERIFY_FAILED` because the sandbox proxy re-terminates TLS. Fix: the Dockerfile accepts an optional BuildKit `cacert` secret; built locally with `--network host --secret id=cacert,...`. TLS verification was not disabled. Normal builds are unaffected.


## Final report (stopped 07:25 IST, Nov 11)

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Inbox Triage | support-ticket-triage | 20 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Day Sheet | clinic-noshow-predictor | 14 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Pantry Saver | pantry-saver | 20 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Exam Runway | exam-runway | 23 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Rent Check | rent-check | 27 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Subscription Sniffer | subscription-sniffer | 20 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Lost and Found Desk | lost-and-found-matcher | 18 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Seating Chart Studio | wedding-seating-planner | 15 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Fair Shift Roster | fair-shift-roster | 34 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Plant Parent | plant-parent | 22 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Household Carbon Coach | household-carbon-coach | 47 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Waiting Room Console | waiting-room-simulator | 31 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Study Pass | study-buddy-matcher | 16 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| School Bus Routes | school-bus-route-planner | 31 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Arc Mixer | playlist-arc-builder | 22 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Pack Weigh-In | trail-pack-optimizer | 19 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Same Time Zone | fair-meeting-time | 21 pass | built+ran | workflow present | yes | no (guide + render.yaml) | Docker Hub 429s were transient |
| Perishable Stock Planner | (none) | - | - | - | no | no | agent hit 5-hour API rate limit mid-build; abandoned |

### Built
17 complete, pushed projects (one branch each), each with README, DEPLOY.md, Dockerfile, CI, tests, sample data. `main` untouched.

### Deployed
None. Render / Hugging Face deploys need the owner's account; render.yaml and DEPLOY.md are ready.

### Blocked
- Docker Hub anonymous 429s (retry after 60-90s fixed each). TLS proxy needed a BuildKit CA secret; verification never disabled.
- Project 17 lost to the API rate limit.
- A stray agent-worktree gitlink is in history on `support-ticket-triage` and `clinic-noshow-predictor` (force-push was denied).
- CI results verified on GitHub only for some branches (lint and Docker COPY bugs caught and fixed on study-buddy-matcher and waiting-room-simulator).

### Decisions
Python + FastAPI + static UI per project; each project got its own palette, type pair and layout from the taste-skill; synthetic data only; no secrets; each README decision carries a one-line reason.

### Next steps
Deploy two to Render, confirm CI green on the newest branches, rebuild perishable-stock-planner, add screenshots to a portfolio page.
