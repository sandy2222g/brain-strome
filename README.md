# Waste Bin Sorter

**Problem.** People bin things wrongly (a greasy pizza box in recycling, a battery in landfill) because the rules are hard to remember.

**Solution.** A multinomial naive Bayes text classifier, written from scratch with Laplace smoothing in log space, maps an item description to one of four bins: recycling, compost, landfill, e-waste. The API returns the probability for each bin.

![demo](docs/demo.png)

**Measured result.** On 32 held-out items (a deterministic stratified 25% split of 128 invented labelled items) the model reaches **65.6%** accuracy vs **25%** for always guessing one bin. Errors are mostly words never seen in training (e.g. "sponge", "mirror"); see Limitations.

## Architecture
```
static/index.html --POST /classify--> api.py (FastAPI) --> core.NaiveBayes (trained at start-up)
                  --GET /metrics----->                      data/items.csv (invented labels)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn binsort.api:app --reload
pytest && ruff check .
docker build -t binsort . && docker run -p 8000:8000 binsort
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Naive Bayes from scratch (no scikit-learn): small dataset, fully explainable, and no heavy dependency in the image.
- Log-space with Laplace smoothing: avoids underflow and zero probabilities for unseen words.
- Deterministic stratified split: results are reproducible and every bin is tested.
- Train on all rows when serving; report accuracy from the held-out split: honest metrics without wasting data.
- Probabilities shown, not just a label: low confidence is visible to the user.

## Limitations
Bag of words with only ~100 training items: unseen words fall back to the prior, and rules that depend on condition (clean vs greasy) are weak. Labels are invented and vary by city, so this is a demo, not a recycling authority. MIT licence.
