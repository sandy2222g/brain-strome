# Report: Tournament Bracket Maker
Decisions: standard seeding, circle-method round robin, Monte Carlo comparison of three formats. Result checked against expectation: round robin > seeded > random for the best team's chances. Local Docker build blocked by Docker Hub 429 twice; CI docker job is the check. `data/teams.json` is tracked, so `COPY data` is valid.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Tournament Bracket Maker | tournament-bracket-maker | 9 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |
