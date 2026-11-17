# Report: Cron Explainer
Decisions: standard Unix cron semantics (day-of-month OR weekday when both set). Rewrote the first English wording for step schedules and plurals after reviewing sample output. No baseline: correctness is checked by hand-worked calendar tests.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Cron Explainer | cron-explainer | 10 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |
