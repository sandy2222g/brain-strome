# Report: Mini Spreadsheet
Decisions: from-scratch parser and engine, no eval(). Excel-compatible precedence. One test fixture error (cell-limit test built only 496 cells, under the 500 limit) was a test bug, fixed in the test. No baseline comparison: correctness is shown by hand-checked tests instead.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Mini Spreadsheet | mini-spreadsheet | 11 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account; local Docker blocked by Docker Hub 429 |
