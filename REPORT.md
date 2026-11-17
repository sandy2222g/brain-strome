# Report: Plant Watering Tree
Decisions: CART from scratch; first run used 400 plants, which gave noisy validation (80 rows), so raised to 1,000 (600/200/200). Removed an unused dataclass field. Fixed three test expectations of mine (clean-rule fit 0.96 not 0.97; feature names in explanations use spaces).

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Plant Watering Tree | plant-watering-tree | 9 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |
