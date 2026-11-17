# Word Ladder Solver

**Problem.** A word ladder turns one word into another by changing one letter at a time, every step a real word (cat → cot → dot → dog). Finding the *shortest* ladder by trial and error is slow and easy to get wrong.

**Solution.** Breadth-first search over a graph where words are nodes and one-letter differences are edges. A bidirectional version searches from both ends at once and does far less work than a one-ended search, with the same answer. The page shows the ladder as tiles with the changed letter highlighted, plus how many words each method had to check.

![demo](docs/demo.png)

**Measured result.** On 200 random pairs of 4-letter words, both searches always agree on whether a ladder exists and on its length; the bidirectional search checked 3,314 words in total against 23,496 for the one-ended search (7.1x less work).

## Data
`data/words.txt`: 381 common 3- and 4-letter English words, typed for this repo (no external source, MIT).

## Architecture
```
static/index.html --GET /ladder?a=&z=, /examples--> api.py (FastAPI)
                                                  --> core.buckets (pattern index c*t) -> core.neighbours
                                                  --> core.bfs and core.bidirectional --> shortest path + work counted
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn wordladder.api:app --reload
pytest && ruff check .
docker build -t wordladder . && docker run -p 8000:8000 wordladder
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Index words by wildcard pattern (`c*t`): finding neighbours becomes a dictionary lookup instead of comparing against every word.
- BFS, not DFS: BFS reaches the goal by the fewest steps first, so the first path found is a shortest one.
- Bidirectional search expanding the smaller frontier: two small searches replace one that fans out much wider.
- Test that both methods agree on length for many pairs: the faster method is only worth it if it is not wrong.
- `valid()` checker for every path: the test suite verifies that each step changes exactly one letter and each word is real.

## Limitations
Small word list, so some real ladders are missing and some pairs show as unreachable; only 3- and 4-letter words; one shortest ladder is returned out of possibly several; no word definitions or difficulty rating.
