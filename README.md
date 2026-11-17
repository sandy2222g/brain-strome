# Typing Speed Coach

**Problem.** Typing tests give one number (WPM) and one blunt error count. They do not say *which* keys you fumble, and a naive letter-by-letter comparison wildly over-counts errors: skip one letter and every letter after it looks wrong.

**Solution.** The coach aligns what you typed against the target with a minimum-edit (Levenshtein) alignment, so each mistake is classified as a substitution, a skipped letter or an extra letter. From that it computes gross and net WPM, accuracy, your weakest keys and most common confusions, then builds a drill from words dense in those letters.

![demo](docs/demo.png)

**Measured result.** Across 5 sample sessions with known injected errors, the aligned count is off by **0.0** errors per session on average; the letter-by-letter count is off by **36.6**.

## Data
`data/sessions.json`: 5 synthetic typing sessions (target text, typed text, seconds) generated for this repo by injecting neighbouring-key substitutions, skipped and doubled letters, with extra mistakes on q, r and e, and the true error count stored for checking. `data/words.txt`: 71 common English words for drills. No real typists. The injected errors never overlap, which is why alignment recovers the count exactly; real mistakes can cancel or overlap, so treat the alignment count as a lower bound.

## Architecture
```
static/index.html --GET /sample, /coach, /evaluation; POST /analyse--> api.py (FastAPI)
                                                                       --> core.align (DP + traceback)
                                                                       --> core.analyse / weak_keys / drill
                                                                       data/sessions.json, data/words.txt
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn typecoach.api:app --reload
pytest && ruff check .
docker build -t typecoach . && docker run -p 8000:8000 typecoach
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Levenshtein alignment with traceback: gives the *kind* of each error, not just a count.
- Net WPM subtracts errors, as typing tests do: speed that costs accuracy is not credited.
- Weak keys need at least 4 attempts: one miss on a rare letter should not top the list.
- Drill words ranked by weak-letter count, then shortness: dense practice, quick to type.
- Spaces ignored in key statistics: they are not what a coach trains.

## Limitations
No keystroke timing, so no per-key latency; no keyboard layouts beyond the sample; fixed sample sessions rather than live typing capture; ties between equal-cost alignments are broken arbitrarily. MIT licence.
