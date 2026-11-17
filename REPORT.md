# Report: Kitchen Stock Reorder
Decisions: reorder-point policy vs weekly fixed order, replayed on held-out days. First version used lead time alone as the protection interval and failed its own 95% service target (13 empty days vs 9 for the baseline); corrected to lead + 1 day and re-measured (2 vs 9). Both runs recorded here, only the corrected one is in the README.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Kitchen Stock Reorder | kitchen-stock-reorder | 10 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
