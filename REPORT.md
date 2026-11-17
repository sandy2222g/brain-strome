# Report: Bloom Spellcheck
Decisions: own tiny dictionary; first suggestions were full of nonsense words ("qduik", "zquik") because they were checked against the same 1% filter, so suggestions now use a second 0.01% filter. Added missing common words (quick, brown, sang) after the first demo flagged valid words. Tightened two weak test assertions (`or` clauses) to exact values (9586 bits, 181 edits).

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Bloom Spellcheck | bloom-spellcheck | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
