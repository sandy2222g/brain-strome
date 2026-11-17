# Report: Text Diff Viewer
Decisions: Myers from scratch, checked against the LCS table on random data. Simplified a confusing loop condition in the backtrack step before testing (3,000 random cases, 0 mismatches). CSS bug found from the screenshot: word highlights were hidden by the row colour rule; fixed with a more specific selector.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Text Diff Viewer | text-diff-viewer | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
