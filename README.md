# Cellular Automata Lab

Tiny rules, big surprises. Explore all 256 one-dimensional "elementary" automata and Conway's Game of Life in the browser.

![demo](docs/demo.png)

## Problem
Cellular automata are a classic way to show how simple local rules create complex behaviour, but most demos show one rule and never check anything.

## Solution
A FastAPI service plus a small web page. It runs any of the 256 elementary rules, ranks them by how compressible their output is (a zlib-based complexity score), and simulates Life patterns, classifying each as still life, oscillator, spaceship or non-repeating.

## Architecture
```
browser (static/index.html, canvas)
   |  GET /rule /rules/top /life /patterns
FastAPI (src/cellauto/api.py)
   |
core.py: rule_row, run_rule, complexity, life_step, classify, population_curve
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn cellauto.api:app --port 8000
pytest
docker build -t cellauto . && docker run -p 8000:8000 cellauto
```
Deploy: see DEPLOY.md (Render or Hugging Face Spaces).

## Verified against known results
- Rule 30 centre column matches OEIS A051023.
- Rule 90 row n has 2^(ones in binary n) cells (Sierpinski triangle).
- Glider: period 4, moves (1,1). Lightweight spaceship: period 4, moves (-2,0).
- R-pentomino settles after 1,103 generations at 116 cells.
- Rule 30 ranks first by compressibility, ahead of 135, 86, 149, 101, 45; rules 0 and 8 are the dullest.

## Design decisions
- Compression ratio as complexity score: it is cheap, deterministic and needs no extra library.
- Sparse set of live cells for Life: the grid is unbounded, so patterns never hit an edge.
- Stateless API: nothing to store, so deployment is trivial.
- Pure-function core: easy to test against published results.

## Limitations
- Compressibility is a proxy for complexity, not a formal measure.
- Elementary rules run on a fixed-width row with dead edges.
- Life classification only looks at a limited number of generations.
- Not deployed; needs the owner's Render/HF account.

Licence: MIT. No external data; all patterns are public-domain classics.
