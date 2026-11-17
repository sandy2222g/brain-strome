# Report: bag-weight-balancer

- Project 75: bag-weight-balancer (domain: travel packing). Subset-sum DP split vs alternating packing (100 g vs 6900 g difference; alternating exceeds the 11 kg limit), checked against brute force; 8 tests, ruff clean. The first sample list happened to make alternating optimal (difference 100 g either way), so the item order and limit were changed to make the comparison honest.
- CI green on 63-70; 71-74 not yet confirmed at last check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Bag Weight Balancer | bag-weight-balancer | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
