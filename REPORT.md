# Report: ab-test-judge

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| A/B Test Judge | ab-test-judge | 7 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |

Decisions: standard-library maths; pooled test with unpooled interval; peeking simulation. A test's expected z (2.39) was wrong; recomputed by hand to 2.50 and fixed the test, not the code.
