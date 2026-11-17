# Report: Campus FAQ Search
Decision: first evaluation crashed on queries whose words appear nowhere in the FAQ; they now count as "no result" instead of an error. Reported accuracy is on my own labelled queries, so it is flagged as a regression check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Campus FAQ Search | campus-faq-search | 7 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |

Blocker: `docker build` failed twice locally with `429 Too Many Requests` from registry-1.docker.io (python:3.12-slim). Not retried a third time.
