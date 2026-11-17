# Report: Raffle Ticket Reality Check
Decisions: exact odds plus seeded simulation. First sample prize tables paid back more than 100% (positive expected value), which contradicted the premise; retuned them to 33-61% before writing tests. Simulated mean vs exact expected value gap on the jackpot game is explained in the README.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Raffle Ticket Reality Check | raffle-ticket-reality | 10 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
