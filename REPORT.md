# Report: Check Digit Validator
Decisions: four validators from scratch plus a typing-mistake detection experiment. Cleaned up a leftover junk line in `random_valid` and replaced a sloppy placeholder test with a real test of the Luhn 09 blind spot. Retook the screenshot after noticing the experiment table had not loaded yet. Local Docker build blocked by Docker Hub 429 twice; CI docker job is the check. No `data/` folder, so the Dockerfile has no `COPY data`.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Check Digit Validator | check-digit-validator | 9 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |
