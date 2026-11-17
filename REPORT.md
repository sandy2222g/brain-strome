# Report: bill-timing-planner

- Project 71: bill-timing-planner (domain: personal cash flow). Daily balance simulation plus greedy due-date moves; sample overdrawn on 9 days, fixed by moving Rent to day 5 and Insurance to day 19; 9 tests, ruff clean. The screenshot viewport cuts off the last verdict line (cosmetic).
- CI: 63-67 green (101-105); 68-70 not yet confirmed.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Bill Timing Planner | bill-timing-planner | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
