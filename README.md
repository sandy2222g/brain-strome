# Unbeatable Tic-Tac-Toe

Play tic-tac-toe against a computer that cannot lose, built with minimax and alpha-beta pruning.

![demo](docs/demo.png)

## Problem
Game-tree search is a core AI idea, but it is usually taught on paper. This project shows it working in a playable app, with the cost of the search measured.

## Solution
A FastAPI service with a click-to-play page. The computer chooses its reply by searching every possible continuation (minimax), preferring faster wins and slower losses. A second implementation adds alpha-beta pruning and the page shows how many positions each needs.

## Architecture
```
browser (you are X) -> GET /move?board= -> api.py -> core.py (winner, minimax, alphabeta, best_move)
                    -> GET /stats      -> node counts, plain vs pruned
```

## Verified
- All 255,168 complete games and 5,478 legal positions are reproduced by the move generator (well-known figures).
- The empty board is a draw under perfect play.
- Plain minimax visits 549,946 positions; alpha-beta reaches the same value with 18,297 (about 30x fewer).
- Exhaustive tests: against every possible human strategy the computer never loses, whether it plays O or X.
- It takes an immediate win over a slower one, and blocks a threat.

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn tttmini.api:app --port 8000
pytest
docker build -t tttmini . && docker run -p 8000:8000 tttmini
```
Local Docker build and `/health` check passed. Deploy: see DEPLOY.md.

## Design decisions
- Board as a 9-character string: hashable, easy to test and send over HTTP.
- Stateless API: the client sends the board, so there is no session to store or lose.
- Cache game values with `lru_cache`: only 5,478 positions exist, so each is solved once.
- Depth-aware tie-break: without it a perfect player may dawdle instead of winning at once.

## Limitations
- Only 3x3; the same search is too slow for larger boards without heuristics and depth limits.
- The computer always plays perfectly, so there is no difficulty setting.
- The first `/stats` call runs the full plain search and takes a few seconds.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. No external data.
