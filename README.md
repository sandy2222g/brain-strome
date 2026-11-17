# Storage Cleanup Picker

**Problem.** A phone or laptop is full. The usual fix is to delete the biggest items, which often includes the holiday videos you actually care about.

**Solution.** Each item gets a size and a "keep" score (0-10). A knapsack dynamic programme picks the set of items that frees at least the space you need while losing the least total keep-value.

![demo](docs/demo.png)

Sample (14 invented items, 5000 MB needed): optimal deletes game installers, app caches and duplicate photos (6100 MB freed, value lost **4**). Deleting biggest-first removes the holiday videos and movies (9000 MB, value lost **14**).

## Architecture
```
static/index.html --POST /pick--> api.py (FastAPI) --> core.optimal / biggest_first
                                                        data/files.json (invented)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn storageclean.api:app --reload
pytest && ruff check .
docker build -t storageclean . && docker run -p 8000:8000 storageclean
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Knapsack DP indexed by MB freed (capped at the target): exact, and fast for realistic sizes.
- Integer MB and integer keep scores: no floating-point ties.
- Verified against brute force on random cases: the DP reconstruction is the likeliest place for a bug.
- Stateless API and no file access: the tool only ranks a list you type in, so it cannot delete anything.

## Limitations
Keep scores are your own judgement; items are all-or-nothing (no partial folders); runtime grows with the target size in MB. File list is invented. MIT licence.
