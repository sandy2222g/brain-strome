# Report: Flat Rent Estimator
Decisions: synthetic data with a known generating rule, so the test can check the learned coefficients against ground truth. Division-by-zero in the baseline R² (constant targets) fixed with a guard.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Flat Rent Estimator | flat-rent-estimator | 9 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |

Blocker: `docker build` failed twice locally with `429 Too Many Requests` from registry-1.docker.io (python:3.12-slim). Not retried a third time.
