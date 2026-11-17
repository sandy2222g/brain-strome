# Autocomplete Trie Search

**Problem.** Search boxes that only match exact prefixes fail the moment someone mistypes: "Londno" returns nothing.

**Solution.** City names are stored in a trie. Typing a prefix returns the most popular matches. When no name starts with the text, a Levenshtein-bounded walk over the same trie returns the closest spellings (1 edit for short queries, 2 for longer ones), fewest edits first, then by popularity. Pruning stops the walk down any branch that is already too far away.

![demo](docs/demo.png)

**Measured result.** On 612 mistyped searches (4 kinds of single typo on every city name of 5+ letters) the right city is in the top 5 **100%** of the time, vs **0.8%** for a prefix-only search.

## Data
`data/cities.csv`: 158 real city names with **synthetic** popularity scores (random, seeded), generated for this repo. City names are public facts; no other data is used. The typos are one edit each by construction, so 100% is an upper bound; real typing errors include double mistakes.

## Architecture
```
static/index.html --GET /suggest?q=--> api.py (FastAPI) --> core.Trie.prefix  (exact prefix, top-k by score)
                  --GET /evaluation->                   --> core.Trie.fuzzy   (row-by-row edit distance during DFS)
                                                            data/cities.csv
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn autocomp.api:app --reload
pytest && ruff check .
docker build -t autocomp . && docker run -p 8000:8000 autocomp
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Trie, not a sorted list: prefix lookup cost depends on the query length, not the dataset size.
- Edit distance computed one row per trie node: siblings share the work of their common prefix.
- Fuzzy only when the prefix matches nothing: otherwise "lon" fills the list with unrelated near-misses such as "Montreal".
- Distance to any prefix of a name, not the whole name: a half-typed misspelling ("Londo") still finds its city.
- Edit budget scales with query length: one typo is plausible in 3 letters, two only in longer queries.

## Limitations
Edits are counted per character (no keyboard-adjacency weights, no transposition as a single edit); words are matched from the start of the whole name, not each word; popularity is synthetic; all in memory. MIT licence.
