# Meeting Notes Summarizer

**Problem.** Meeting notes pile up unread. People want the three sentences that matter and a list of who promised what by when.

**Solution.** Extractive summarisation with **TextRank**: sentences become nodes in a graph, edges are TF-IDF cosine similarities, and PageRank (power iteration, written from scratch) scores them. The top sentences are returned in their original order. A pattern finds action items such as "Marcus will prepare the mockups by Friday".

![demo](docs/demo.png)

**Measured result (small!).** On 4 invented meetings with hand-labelled key sentences, **41.7%** of TextRank's top-3 sentences are key sentences, vs **33.3%** for the "first three sentences" baseline. With only 4 meetings this is a smoke test, not evidence of general quality; the README says so on purpose. Action items are found exactly in all 4 meetings (6 items, owners and due dates correct).

## Architecture
```
static/index.html --POST /summarise--> api.py (FastAPI) --> core.summarise: split -> TF-IDF sim -> TextRank
                  --GET /metrics----->                      core.action_items: regex Name will|should ... by|before ...
                                                            data/meetings.json (invented transcripts + labels)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn notesum.api:app --reload
pytest && ruff check .
docker build -t notesum . && docker run -p 8000:8000 notesum
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Extractive, not generative: no model download, no hallucinated facts, every summary line is a real sentence.
- TextRank with TF-IDF edges: unsupervised, so it needs no training data.
- PageRank verified on a hand-solved star graph: the ranking code is tested against numbers, not just "looks right".
- Regex for action items: predictable and explainable; limits stated below.
- Metrics endpoint with labelled meetings: any change to scoring can be compared with the baseline.

## Limitations
Only 4 labelled meetings, so the accuracy figure is weak evidence. Action items need the pattern "Capitalised-name will/should ...", so pronouns, passive voice or lowercase names are missed, and any capitalised word before "will" counts as a person. No speaker labels, timestamps or languages other than English. MIT licence.
