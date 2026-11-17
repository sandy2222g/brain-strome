# Flat Rent Estimator

**Problem.** Renters and landlords want a quick sense of a fair monthly rent and, more usefully, *why*: what does one more bedroom or one more kilometre from the centre cost?

**Solution.** A ridge regression fitted from scratch (standardised features, normal equations, Gauss-Jordan solver; no numpy or scikit-learn). The API predicts a rent and reports the price change per unit of each feature.

![demo](docs/demo.png)

**Measured result.** On 48 held-out listings (a deterministic 80/20 split of 240) the model has RMSE **$54.5** and R² **0.964**; always predicting the mean rent gives RMSE $287.2 and R² -0.001. The learned effects (+$8.9 per m², +$62 per bedroom, -$22.5 per km, -$3.3 per year) are close to the rule used to generate the data (+9.2, +55, -22, -3.5).

## Data
Synthetic and generated for this repo (`data/rents.csv`): rent = 320 + 9.2·area + 55·bedrooms − 22·distance − 3.5·age + noise (σ = $55). No real listings or personal data. Because the data is linear by construction, the high R² shows the code works, not that real rents are this predictable.

## Architecture
```
static/index.html --POST /estimate--> api.py (FastAPI) --> core.Model.predict
                  --GET /metrics ---->                      core.fit: standardise -> (XᵀX + λI)w = Xᵀy -> solve
                                                            data/rents.csv (synthetic)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn rentest.api:app --reload
pytest && ruff check .
docker build -t rentest . && docker run -p 8000:8000 rentest
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Ridge (L2) with standardised features: stable when features correlate (area and bedrooms), and coefficients are comparable.
- Closed-form solve, not gradient descent: exact, no learning-rate tuning, trivially testable.
- Intercept left unpenalised: the baseline level of rent should not be shrunk.
- Held-out split with fixed rule: reproducible metrics shown in the UI.
- Input ranges validated in the API: stops extrapolation far outside the training data.

## Limitations
Linear model only (no interactions, no neighbourhood effects); trained on synthetic data, so numbers say nothing about any real city; at serving time the model is refit on all 240 rows. MIT licence.
