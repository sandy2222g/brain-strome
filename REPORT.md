# Report: fair-teams-picker

- Project 76: fair-teams-picker (domain: pick-up sports). Exhaustive equal-size split with pair rules; gap 1 vs captains' picks gap 5 plus a broken keep-together rule; checked against independent brute force; 9 tests, ruff clean.
- CI green on 63-74 (runs 101-112); 75 not yet confirmed at last check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Fair Teams Picker | fair-teams-picker | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
