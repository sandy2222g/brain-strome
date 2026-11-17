# Report: Coupon Stack Chooser
Decision: documented a single discount order instead of searching orders, because real stores fix it.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Coupon Stack Chooser | coupon-stack-chooser | 9 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |

Blocker: `docker build` failed twice locally with `429 Too Many Requests` from registry-1.docker.io (python:3.12-slim). Not retried a third time.
