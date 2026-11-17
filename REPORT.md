# Report: Palette Extractor
Decision: only project so far that takes a file upload, so I added a 5 MB cap and a bundled generated sample (no third-party photo, no licence issue). Adds pillow and python-multipart to requirements.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Palette Extractor | palette-extractor | 8 pass | builds, /health and /palette ok locally | workflow present | yes | no | deploy needs owner account |

Fix: CI docker job failed (`COPY data ./data: "/data": not found`). This project has no data directory (git does not track empty directories, but my local copy had one). Removed the `COPY data` line from the Dockerfile. The local build passed earlier only because of that empty directory.
