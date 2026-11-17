# Report: Dither Lab
Decisions: pure Python (no Pillow). First scoring used 4x4 blocks, which made ordered dithering beat Floyd-Steinberg; found the bias (window equals the Bayer tile), switched to 5x5 windows at every position, kept both results as a test and a README finding. Fixed two long lines for ruff. Screenshot first cut off the results table, so the preview images were made smaller.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Dither Lab | dither-lab | 10 pass | builds, /health ok locally | workflow present | yes | no | deploy needs owner account |

Fix: CI docker job failed because Dockerfile copied an empty, untracked data/ directory (data is generated in code). Removed that COPY line. Found by reading CI results, not by the local build, which had the empty directory on disk.
