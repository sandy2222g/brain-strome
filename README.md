# Flashcard Scheduler

![demo](docs/demo.png)

## Problem
Students cram flashcards on a fixed rhythm and forget most of them, or review everything daily and burn hours. Which schedule keeps a deck remembered for the least effort?

## Solution
Simulate a learner who forgets, then run four review schedules over 60 days on a 12-card deck, averaged over 40 seeded learners. Recall chance after `gap` days is exp(-gap / S); each success multiplies the card's stability S by (1 + 2 / hardness), each miss cuts it to 40%.

| Schedule | Reviews per card | Recalled on day 60 |
|---|---|---|
| Every day | 60 | 94% |
| Every 3 days | 20 | 30% |
| Leitner boxes (1, 2, 4, 8, 16, 32 days) | 24 | 69% |
| SM-2 style (gaps grow with success) | 27 | **85%** |

SM-2 style gets within 9 points of daily review with 44% of the reviews. It does cost more reviews than a fixed 3-day gap, because misses pull cards back to short intervals; the fixed gap is cheap only because it forgets almost everything.

## Architecture
```
data/deck.json or POST body -> core.build (validate) -> core._simulate (one seeded learner, one schedule)
                            -> core.compare (average over seeds) -> FastAPI /compare -> static/index.html
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn recall.api:app --port 8000
pytest -q && ruff check .
docker build -t recall . && docker run -p 8000:8000 recall
```
Endpoints: `GET /health`, `GET /sample`, `POST /compare`, `GET /`. Deploy: see `DEPLOY.md`.

## Design decisions
- Simulation instead of real learner data: no personal data needed, and every schedule faces the same simulated memory.
- Exponential forgetting with growing stability: the simplest model that makes spacing matter.
- Seeded learners, 40 runs averaged: the numbers are repeatable and not a lucky draw.
- Recall measured as expected probability on the last day: removes the noise of one final coin flip.
- "Every day" as an upper reference: it shows what the other schedules are trying to approximate cheaply.

## Limitations
- The forgetting model is an assumption; real memory varies by person and card, so treat the numbers as illustrative.
- SM-2 is simplified (fixed grade, no quality scale).
- Deck and hardness values are invented (MIT).
