# Report: morning-routine-planner

- Project 79: morning-routine-planner (domain: getting ready in the morning). Dependency scheduling for one person with hands-free tasks; sample: wake 07:31 (44 min) vs 07:22 one by one, lower bound 25 min; matches brute force on the sample; 10 tests, ruff clean. My first version was a plain critical-path calculation that assumed unlimited helpers (the shower and breakfast could overlap), which gave 07:50 and was unrealistic; I rewrote it for one person with hands-free tasks.
- CI green on 63-74; 75-78 not yet confirmed at last check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Morning Routine Planner | morning-routine-planner | 10 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
