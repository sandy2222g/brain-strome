# Report: Receipt Line Reader
Decisions: rule-based parser over integer cents. One ground-truth label (receipt 4) was wrong, not the parser, and was corrected and disclosed in the README. 100% accuracy is on same-author synthetic receipts (caveat in README).

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Receipt Line Reader | receipt-line-reader | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
