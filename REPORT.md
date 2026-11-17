# Report: Sorting Race
Decisions: count comparisons rather than time; naive quicksort pivot kept on purpose and documented. Test expectation fixed after measuring: quick vs heap on sorted input is 7.7x, not 10x. Dockerfile had no `COPY data` line from the start (lesson from the dither-lab CI failure). Docker build and /health checked locally.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Sorting Race | sorting-race | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
