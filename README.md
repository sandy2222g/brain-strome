# Weather Outfit Picker

**Problem.** "Is it a coat day?" depends on temperature, wind and rain together, and a single temperature threshold gets windy and wet days wrong.

**Solution.** A multinomial logistic (softmax) regression, written from scratch with batch gradient descent, predicts one of four outfits (light, jumper, coat, raincoat) and returns a probability for each, so uncertain days are visible.

![demo](docs/demo.png)

**Measured result.** On 60 held-out days the model is right **85%** of the time vs **33%** for always guessing the most common outfit.

## Data
`data/days.csv`: 240 synthetic days (temperature, wind, rain, outfit), generated for this repo from a feels-like rule (temperature minus 0.15 x wind; rain of 2 mm or more means raincoat) with 7% of labels randomly flipped to mimic personal taste. No real data. Because the labels come from a rule the model can learn, real-world accuracy would be lower.

## Architecture
```
static/index.html --POST /recommend--> api.py (FastAPI) --> core.train (softmax regression, trained once, cached)
                  --GET /evaluation-->                      data/days.csv
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn outfitpick.api:app --reload
pytest && ruff check .
docker build -t outfitpick . && docker run -p 8000:8000 outfitpick
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Softmax regression, not a library model: shows the maths and needs no ML dependency.
- Standardised features: gradient descent converges quickly when temperature and rain share a scale.
- L2 penalty of 1e-3: stops the weights growing on the few noisy labels.
- Returns all four probabilities: a 48/47 split between jumper and coat is honest, a bare label is not.
- Fixed every-4th-row holdout: deterministic, so the reported accuracy is reproducible.

## Limitations
Synthetic labels; one person's taste; no humidity, sun or time of day; linear decision boundaries only. MIT licence.
