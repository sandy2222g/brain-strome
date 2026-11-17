# Report: Gradient Descent Lab
Decisions: pure Python, one feature, compared with the exact solution. Learned from the previous CI failures: this project has no `data/` folder, so the Dockerfile `COPY data` line was removed before the first push. Local Docker build blocked by Docker Hub 429 twice; CI docker job is the check.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Gradient Descent Lab | gradient-descent-lab | 9 pass | local build blocked (Docker Hub 429 twice); CI docker job is the check | workflow present | yes | no | deploy needs owner account |
