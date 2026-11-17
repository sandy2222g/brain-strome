# Report: Word Ladder Solver
Decisions: own small word list (no licence questions); bidirectional search compared against plain BFS on 200 random pairs (7.1x less work, equal lengths). Replaced an example whose word was missing from the list (gold to dust became gold to mint). Fixed a wrong test that expected cat to dog to be unreachable (dot links them).

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Word Ladder Solver | word-ladder-solver | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
