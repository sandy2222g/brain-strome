# Campus FAQ Search

**Problem.** Students ask the same questions in different words ("extend my book loan" vs "renew a library book"). Keyword lookup misses them and a chatbot is overkill.

**Solution.** A TF-IDF search engine written from scratch: light stemming, stop-word removal, sublinear term frequency, smoothed inverse document frequency and cosine similarity. The question text counts double against the answer text.

![demo](docs/demo.png)

**Measured result.** On 32 paraphrased test questions (2 per FAQ, 16 invented FAQs) TF-IDF puts the right answer first **90.6%** of the time, vs **81.2%** for plain word overlap (mean reciprocal rank 0.906 vs 0.854). Caveat: I wrote the test questions myself, so treat this as a regression check, not a benchmark.

## Architecture
```
static/index.html --POST /search--> api.py (FastAPI) --> core.Index (TF-IDF vectors built at start-up)
                  --GET /metrics -->                      data/faq.json (invented FAQ + labelled queries)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn faqsearch.api:app --reload
pytest && ruff check .
docker build -t faqsearch . && docker run -p 8000:8000 faqsearch
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- TF-IDF, not embeddings: no model download, instant start-up, and every score can be explained.
- Smoothed idf and sublinear tf: stops one repeated word dominating and avoids divide-by-zero.
- Question weighted double: users' wording is closer to the question than to the answer.
- Evaluation shipped with the code: `/metrics` recomputes accuracy from labelled queries, so changes can be checked.
- Unknown words give a clear 422, not a random answer.

## Limitations
No synonyms ("fitness centre" never matches "gym"; those queries return nothing), no spelling correction, and only 16 invented FAQs, so scores will fall on real data. A sentence-embedding model would fix synonyms at the cost of size. MIT licence.
