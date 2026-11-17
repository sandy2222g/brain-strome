# Report: Moon Phase Calendar
Decisions: Meeus formulas, with a mean-month baseline for comparison. Reference full moons for 2024 typed from public almanac tables; the corrected model agrees within 22 minutes, which also cross-checks that I typed them correctly. First age/illumination used the fixed mean month (half-day error); switched to real new moons either side. Tightened a sloppy test (an `or` that always passed). Also noticed, from CI, that two earlier projects (dither-lab, plant-watering-tree) failed because their Dockerfile copied an untracked empty `data/` folder; fixed on those branches. For this project `data/` is tracked, and the Docker build and /health check were done locally.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Moon Phase Calendar | moon-phase-calendar | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
