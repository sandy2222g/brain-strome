# Report: appliance-power-cost

- Project 72: appliance-power-cost (domain: household electricity). Time-of-use cost per appliance and off-peak shifting saving (146.42 total, 43.32 saved; flat rate says 140.70); 8 tests, ruff clean.
- CI green on 63-70 (runs 101-108 and 106-108 confirmed); 71 running at last check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Appliance Power Cost | appliance-power-cost | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
