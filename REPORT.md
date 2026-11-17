# Report: potluck-dish-matcher

- Project 81: potluck-dish-matcher (domain: shared meals). Maximum bipartite matching (Kuhn) fills 7 of 7 slots vs 6 for first-come; checked against exhaustive search on random cases; 8 tests, ruff clean. A first test failure was a bug in my brute-force helper (it only considered the first slots when guests were fewer than slots), not in the matcher; the helper was fixed.
- Docker: the first local build hit Docker Hub `429 Too Many Requests` (python:3.12-slim manifest); the single retry after a short wait succeeded and /health returned ok, so the 'builds' entry below is verified.
- CI green on 63-78; 79 and 80 not yet confirmed at last check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Potluck Dish Matcher | potluck-dish-matcher | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
