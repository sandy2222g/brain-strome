# Text Diff Viewer

**Problem.** "What changed between these two versions?" is hard to answer by eye, and a naive comparison either misses edits or reports far more changes than needed.

**Solution.** Myers' diff algorithm (the one behind `git diff`), written from scratch. It finds the *smallest* set of added and deleted lines, then, inside each changed line, a second word-level diff highlights exactly which words moved. The page shows both versions side by side.

![demo](docs/demo.png)

**Measured result.** 1,500 random sequence pairs in the tests: the script always rebuilds both inputs exactly and always has the same number of edits as the textbook O(nm) table (the true minimum). On two 2,000-line files with 2 edited lines, Myers takes about 1 ms against 420 ms for the table (about 440x faster).

## Data
`data/a.txt`, `data/b.txt`: two versions of a short pancake recipe, written for this repo (MIT).

## Architecture
```
static/index.html --POST /diff {a, b}--> api.py (FastAPI)
                                        --> core.myers (lines) -> core.pair_changes
                                        --> core.myers (words, per changed line) -> rows with highlights
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn textdiff.api:app --reload
pytest && ruff check .
docker build -t textdiff . && docker run -p 8000:8000 textdiff
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Myers' O(ND) algorithm: cost grows with the number of edits D, so two similar big files are cheap.
- Check against the O(nm) table on random inputs: a diff that is lossless but not minimal would pass casual testing, so minimality is tested directly.
- Lines first, words second: a line diff alone makes a one-word edit look like a rewrite.
- Words and punctuation as separate tokens: a changed comma or a plural is highlighted precisely.
- Limit of 4,000 lines per side: the algorithm stores one frontier per edit, so memory must be bounded on a public server.

## Limitations
No moved-block detection (a moved paragraph shows as a delete plus an add); added and removed line blocks of different sizes are paired top-to-bottom, which is not always the nicest pairing; no unified or patch output; no ignore-whitespace option; large inputs with many edits are slower and heavier on memory.
