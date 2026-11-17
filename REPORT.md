# Report: Waste Bin Sorter
Decisions: first dataset (80 rows) gave 65% held-out accuracy; I added 48 more rows and it stayed 65.6%. Errors come from unseen words, so I report the real number rather than tuning the test split.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Waste Bin Sorter | waste-bin-sorter | 8 pass | local build blocked (Docker Hub 429 twice); relies on CI docker job | workflow present | yes | no | deploy needs owner account |

Blocker: `docker build` failed twice locally with `429 Too Many Requests` from registry-1.docker.io (base image python:3.12-slim). Not retried a third time; the CI docker job is the check for this branch.
