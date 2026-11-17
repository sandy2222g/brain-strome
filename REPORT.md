# Report: Palette Extractor
Decision: only project so far that takes a file upload, so I added a 5 MB cap and a bundled generated sample (no third-party photo, no licence issue). Adds pillow and python-multipart to requirements.

| project | branch | tests | docker | CI | pushed | deployed | blockers |
|---|---|---|---|---|---|---|---|
| Palette Extractor | palette-extractor | 8 pass | builds, /health and /palette ok locally | workflow present | yes | no | deploy needs owner account |
