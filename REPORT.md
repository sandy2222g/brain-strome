# Report: Language Guesser
Decisions: character-trigram naive Bayes vs single-letter baseline on a held-out split; parallel original sentences so the five languages are compared on the same content. 100% held-out accuracy is on 30 sentences (caveat in README).

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Language Guesser | language-guesser | 9 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |
