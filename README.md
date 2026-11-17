# Potluck Dish Matcher

![demo](docs/demo.png)

## Problem
For a shared meal you need a spread (mains, salad, dessert, drinks, bread), but guests can only bring certain things. If people just pick the first dish they can, a slot like "bread" stays empty while a guest who could have filled it brings nothing.

## Solution
Treat it as a bipartite matching between guests and dish slots and solve it with augmenting paths (Kuhn's algorithm), taking the guests with the fewest options first. Sample (7 invented guests, 7 slots): all 7 slots are filled. A first-come baseline fills only 6, leaving a bread slot empty while Gia brings nothing. Tests compare against exhaustive search on random small cases.

## Architecture
```mermaid
flowchart LR
  UI[static page] -->|POST /match| API[FastAPI api.py]
  API --> Core[core.py: match, first_come]
  Core --> Data[data/party.json]
```

## Setup
```bash
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn potluck.api:app --port 8000
PYTHONPATH=src pytest
docker build -t potluck . && docker run -p 8000:8000 potluck
```
Deploy: see [DEPLOY.md](DEPLOY.md) (Render or Hugging Face Spaces).

## Design decisions
- Augmenting-path matching: it finds the maximum number of filled slots, and a greedy rule cannot guarantee that.
- Pickiest guests first: a cheap ordering that usually reduces re-assignments.
- One dish per guest: keeps the load fair, and matches how most potlucks work.
- Unfilled slots and idle guests are reported: the host can see exactly what is missing.

## Limitations
- No quantity (servings) or dietary constraints beyond what guests say they can bring.
- No preference ranking among dishes a guest can bring.
- Guests and dishes are invented.

Data: invented, MIT licence.
