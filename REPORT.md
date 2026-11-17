# Report: Elevator Dispatch Simulator
Decisions: event loop stepping one floor at a time; found and fixed a livelock (full lift ping-ponging between waiting floors) and kept a regression test. A hand-computed test expectation was wrong (ride time includes boarding doors), fixed the test, not the code.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Elevator Dispatch Simulator | elevator-dispatch-sim | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
