# Report: Meeting Notes Summarizer
Decisions: honest small-sample metric (TextRank 0.417 vs lead-3 0.333, 4 meetings) stated as a smoke test. Action-item regex first matched "Welcome to" and "Tuesday to"; restricted to "will|should" and fixed the "by next Thursday" date. Test data reworded so "Registration for the run will..." is not a false hit.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Meeting Notes Summarizer | meeting-notes-summarizer | 8 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
