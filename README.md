# Markov Name Maker

**Problem.** Writers, game designers and map makers need believable place names, and lists of random syllables sound wrong. How do you make names that *sound* English without copying real ones?

**Solution.** A character n-gram language model: it learns which letters tend to follow the previous few letters in 142 village names, then samples new names letter by letter. The context length is chosen on held-out names the model never trained on, not by guessing. You can force a starting prefix ("wil" gives Willow-like names) and the page shows the held-out score of each context length.

![demo](docs/demo.png)

**Measured result.** Surprise on 29 held-out names, in bits per letter (lower is better): 0 letters of context 4.413, 1 letter 3.907, **2 letters 3.683**, 3 letters 4.030, 4 letters 4.353. Context helps up to two letters, after which the model memorises the small training set and gets worse. Generated names are always new (not in the training list) and 4-14 letters long.

## Data
`data/villages.txt`: 142 English-style village names typed for this repo (fictional or generic, MIT). Not scraped from any gazetteer.

## Architecture
```
static/index.html --GET /generate?n=&order=&seed=&prefix=, /scores--> api.py (FastAPI)
  --> core.split (every 5th name held out) -> core.evaluate (orders 0-4) -> best order at start-up
  --> core.Model.fit (counts per context) -> sample (seeded RNG) -> filter: new, 4-14 letters
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn namemaker.api:app --reload
pytest && ruff check .
docker build -t namemaker . && docker run -p 8000:8000 namemaker
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Choose the context length on held-out data: training score always favours longer context, so it would pick the worst model.
- Add-k smoothing (k = 0.1) plus backing off to shorter contexts: unseen letter combinations get a small probability instead of crashing or scoring infinity.
- Fixed random seed per request: the same request returns the same names, which makes bugs reproducible and tests exact.
- Only return names that are not in the training list: a generator that hands back its training data is not generating.
- Plain counts and dictionaries, no ML framework: the whole model is about 60 lines and easy to explain in an interview.

## Limitations
Tiny training set (142 names), so the model has seen limited spelling patterns and quality varies; a few outputs are real words ("Bravery") or awkward; the score is bits per letter, which measures spelling plausibility, not whether a name sounds good; one language style only; held-out set of 29 names makes the score differences small but visible.
