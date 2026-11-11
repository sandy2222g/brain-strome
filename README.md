# Carry-on Capsule

![demo](docs/demo.png)

## Problem
A carry-on has a weight allowance and you own far more clothes than fit. Which pieces give the most outfits?

## Solution
An outfit is a top, a bottom and shoes of one style (smart or casual; neutral pieces work with both). A layer is optional and multiplies the count. On the sample wardrobe (18 pieces, 3,200 g):

| Method | Outfits | Grams |
|---|---|---|
| Pack in listed order (favourites first) | 0 | 2,960 |
| Lightest first | 12 | 2,880 |
| Exact search over every subset | **24** | 3,120 |

Packing favourites first leaves no shoes at all; lightest-first packs plenty but mismatches styles.

## Architecture
```
data/wardrobe.json or POST body -> core.pack_in_order / lightest_first / best_capsule (all subsets)
                                -> FastAPI /capsule -> static/index.html (three boarding-pass cards)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn capsule.api:app --port 8000
pytest -q && ruff check .
docker build -t capsule . && docker run -p 8000:8000 capsule
```
Endpoints: `GET /health`, `GET /sample`, `POST /capsule`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Exact search over all subsets, capped at 20 items: 2^20 subsets is about a second and cannot be beaten.
- Outfits counted per style: a neutral top worn with smart or casual bottoms really is a different look.
- Layers multiply rather than add: a jacket changes every outfit, not just one.
- Lightest-first as the second baseline: a "greedy by marginal outfits per gram" heuristic stalls at zero because no single garment makes an outfit.
- Lightest weight breaks ties: among equal outfit counts you carry less.

## Limitations
- Style is a three-value label; no colour matching, weather or trip length.
- Exact search is exponential, so the wardrobe is capped at 20 pieces.
- Outfit count rewards variety, not quality; garments are invented (MIT).
