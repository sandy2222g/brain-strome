# Report: maze-lab

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Maze Lab | maze-lab | 10 pass | local build blocked by Docker Hub 429 twice (exact: unexpected status from HEAD request ... 429 Too Many Requests); CI job builds it | workflow present | yes | no | deploy needs owner account |

Decisions: perfect mazes so all solvers must agree; seeded generators; cached comparison.
