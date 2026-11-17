# PageRank Lab

PageRank implemented from scratch and applied to a small invented network of a town's websites.

![demo](docs/demo.png)

## Problem
Ranking pages by how many links they receive is easy to game and ignores who is linking. PageRank scores a page by the importance of the pages that point to it.

## Solution
Power-iteration PageRank with damping and correct handling of dangling pages (pages with no outgoing links). An independent solver (Gaussian elimination on the same equations) checks the result. A page lets you move the damping slider and compare PageRank with plain link counts, and `/rank` accepts your own link graph.

## Architecture
```
browser bars -> GET /town?damping= -> api.py -> core.py (pagerank, pagerank_exact, ranking, indegree_ranking)
             -> POST /rank (your own graph)
```

## Results (damping 0.85)
| page | PageRank | links in |
|---|---|---|
| town-hall | 26.8% | 8 |
| market | 15.1% | 4 |
| clinic | 7.05% | 1 |
| sports-club | 7.00% | 3 |
| gazette | 1.4% | 0 |

The clinic has one inbound link, from the town hall, yet slightly outranks the sports club with three.

## Verified
- Scores sum to 1; power iteration matches the direct linear solve to 1e-9.
- Damping 0 gives every page 1/11.
- A page nobody links to scores exactly 0.15/11 (only the random-jump share).
- A symmetric two-page graph gives 0.5 each.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn prlab.api:app --port 8000
pytest
docker build -t prlab . && docker run -p 8000:8000 prlab
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Dangling pages spread their rank evenly: otherwise total rank leaks away and scores stop summing to 1.
- Check against a direct solve: two different methods agreeing is stronger evidence than one.
- Invented town network: no scraped data, no licence questions.
- Graph size capped at 200 pages on `/rank`: pure-Python iteration is fine for small graphs.

## Limitations
- Small graphs only; real web scale needs sparse matrices and distributed computation.
- No link-spam handling or personalised PageRank.
- Damping fixed per request; convergence uses a tight L1 tolerance and a 1,000-iteration cap.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. The network is invented.
