# Report: Elo Rating League
Decisions: sequential Elo vs win-rate baseline on a deliberately lopsided synthetic schedule. Accuracy gap (73% vs 68% on 60 games) is within noise, said so in the README; the rank correlation gap (0.877 vs 0.775) is the main result. Ruff E741 (variable `l`) fixed by renaming.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Elo Rating League | elo-rating-league | 10 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
