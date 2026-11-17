# Bloom Spellcheck

**Problem.** A spell checker needs to ask "is this a word?" millions of times a second, and storing the whole dictionary (every word as a string) is large when the checker lives in a browser, a phone or a cache in front of a service.

**Solution.** A Bloom filter written from scratch: a bit array plus `k` hash functions that answers "definitely not a word" or "probably a word". It never forgets a real word, it is about 100x smaller than a Python set of the same words, and the slider on the page trades size against how often it wrongly accepts a typo. Typos get suggestions by trying all one-edit variants and keeping those the filter accepts.

![demo](docs/demo.png)

**Measured result.** For the 496-word dictionary at a 1% target: 595 bytes against 55,548 bytes for a set (93x smaller), 7 hash functions, measured false-positive rate 1.09% against 1.00% predicted by theory. Tests check the rate at 5% and 1% targets and confirm zero false negatives at 20%, 1% and 0.1%.

## Data
`data/words.txt`: 496 common English words, typed for this repo (no external source, MIT). Real dictionaries have 100,000+ words, where the size gap is much larger in absolute terms.

## Architecture
```
static/index.html --GET /check?text=&p=, /sample--> api.py (FastAPI)
  --> core.size_for(n, p) -> m bits, k hashes
  --> core.Bloom (bytearray + blake2b double hashing) <-- built once per p, cached
  --> core.check_text: unknown words -> edits1 -> candidates found in a stricter filter (p = 0.01%)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn bloomcheck.api:app --reload
pytest && ruff check .
docker build -t bloomcheck . && docker run -p 8000:8000 bloomcheck
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Size from the textbook formulas (m = -n ln p / (ln 2)^2, k = (m/n) ln 2): the filter is as small as the target error rate allows.
- One blake2b hash split in two and combined as h1 + i*h2: k hash functions for the price of one, with no loss of accuracy in practice.
- Suggestions use a second, stricter filter (0.01%): at 1% a third of suggestions would be nonsense words that happen to pass.
- A `bytearray` for the bits: compact and built in, no dependencies.
- Measure the false-positive rate on random non-words and compare to theory: shows the maths holds and is the test that catches a broken hash.

## Limitations
It cannot list or remove words (a plain Bloom filter supports neither); about 1 typo in 100 slips through at the 1% setting, and suggestions can still include a bogus word (visible in the demo: "mokn") because even the strict filter has a 0.01% error rate per candidate; the dictionary is tiny and has no word frequencies, so suggestions are alphabetical, not ranked; only one-edit typos are suggested.
