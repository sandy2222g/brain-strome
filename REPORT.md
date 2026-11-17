# Report: unit-price-checker

- Project 69: unit-price-checker (domain: shelf prices). Unit conversion and price per 100 g; the cheapest pack is the 2 lb pack, not the biggest (5 kg sack is +16.6%); 8 tests, ruff clean. First draft of my test expectations assumed the 1 kg bag was cheapest; the oz/lb conversion made the 2 lb pack cheaper, so tests were corrected to the computed values.
- CI green on 63-67 (runs 101-105); 68 in progress at last check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Unit Price Checker | unit-price-checker | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
