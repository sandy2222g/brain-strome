# Report: Waste Bin Sorter
Decisions: first dataset (80 rows) gave 65% held-out accuracy; I added 48 more rows and it stayed 65.6%. Errors come from unseen words, so I report the real number rather than tuning the test split.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Waste Bin Sorter | waste-bin-sorter | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
