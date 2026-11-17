# Report: Town Bridge Finder
Decisions: Tarjan bridges and articulation points, checked against brute force on the town and on 400 random graphs (a first run failed because bridges came back as (parent, child) tuples; normalised to sorted tuples). Local Docker build blocked by Docker Hub 429 twice; CI docker job is the check. `data/town.json` is tracked, so `COPY data` is valid.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Town Bridge Finder | town-bridge-finder | 8 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |
