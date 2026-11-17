# Language Guesser

**Problem.** Apps often need to know what language a piece of text is in (to pick a spell-checker, a voice, a translation direction) before they know anything else about it.

**Solution.** For each language the model counts how often every sequence of three characters (a character trigram, including the space at word edges) appears in training sentences. A new text is scored under each language with Laplace-smoothed log probabilities, the scores are normalised to percentages, and the best language wins. This is naive Bayes over character n-grams, written from scratch with the standard library.

![demo](docs/demo.png)

**Measured result.** Trained on 14 sentences per language and tested on 6 unseen sentences per language (30 in total, 5 languages), trigrams are **100%** right and a single-letter model **97%**. On the first 20 characters only (a very short snippet), trigrams keep **93%** while single letters drop to **70%**; guessing would give 20%. The test set is tiny and the sentences are translations of the same ideas, so treat the numbers as a sanity check rather than a benchmark.

## Data
`data/sentences.json`: 20 everyday sentences in each of English, Spanish, French, German and Italian, written for this repo as translations of the same 20 ideas (a small parallel corpus). Original text, no external corpus. The web app uses all 20 per language; the evaluation uses 14 to train and 6 to test (the page's example sentences come from the training set, so their 100% is not evidence of accuracy).

## Architecture
```
static/index.html --POST /guess; GET /evaluation, /examples--> api.py (FastAPI)
                                                              --> core.Model (n-gram counts, smoothed log scores)
                                                              data/sentences.json
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn langguess.api:app --reload
pytest && ruff check .
docker build -t langguess . && docker run -p 8000:8000 langguess
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Character trigrams, not words: they work on short text, misspellings and unseen words.
- Pad with spaces: the model sees word starts and ends ("th" at the start of a word is different from inside one).
- Laplace smoothing (add 0.5): a trigram never seen in one language must not make its probability zero.
- Normalise scores to probabilities: users deserve to see "55% sure" for a short word, not just a label.
- Compare against a single-letter model on the same split: shows what the extra context buys.

## Limitations
Five languages, written in Latin script; an unsupported language (Russian, say) still gets one of the five labels; very short or mixed-language text is genuinely ambiguous (a bare "ok" is guessed as English at 57%); tiny training set. MIT licence.
