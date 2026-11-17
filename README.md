# Gradient Descent Lab

**Problem.** Almost every machine-learning model is trained by gradient descent, yet two settings, the learning rate and whether the inputs are scaled, decide whether training works, crawls or blows up. Tutorials say so; few let you break it and see it.

**Solution.** Linear regression by gradient descent written from scratch in pure Python, fitting a made-up scooter fare (dollars) to distance (km). The page has a learning-rate slider (log scale), a steps slider and a feature-scaling switch, plots the fitted line against the exact least-squares answer, plots the loss curve, and fills a table of "steps needed" for seven learning rates, scaled and unscaled.

![demo](docs/demo.png)

**Measured result.** The exact answer is 0.837 dollars per km + 1.65 (hidden truth 0.85 + 1.50). With scaled inputs gradient descent reaches the same line (error under 0.001) and gets within 1% of the best loss in 22 steps at rate 0.1, or 1 step at 0.5. With raw kilometres, rates of 0.03 and above diverge, and the safe rate 0.01 is still not within 1% after 400 steps. Rate 1.2 diverges even with scaling.

## Data
Generated in code by `make_data()`: 120 synthetic trips, distance 0.5-15 km, fare = 1.50 + 0.85 x km + Gaussian noise (sd 0.7). No files, nothing to license (MIT).

## Architecture
```
static/index.html (SVG charts) --GET /descend?lr=&steps=&scale=, /experiment, /data--> api.py (FastAPI)
   core.closed_form  (exact answer)
   core.descend      (gradient steps, optional standardising, divergence guard) -> losses, w, b
   core.experiment   (all learning rates, both modes)
```

## Setup
```
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn gdlab.api:app --reload
pytest && ruff check .
docker build -t gdlab . && docker run -p 8000:8000 gdlab
```
Deploy: see [DEPLOY.md](DEPLOY.md).

## Design decisions
- Compare against the closed-form solution: gradient descent needs a ground truth, and for a line the exact answer is one formula.
- Scaling as a switch, with the weights converted back to kilometres afterwards: the lesson is visible and the final line is comparable.
- Stop and flag divergence when the loss passes 1e12 or turns non-finite: a runaway run would otherwise return NaN or hang the server.
- "Steps to within 1% of the best loss" as the speed measure: more meaningful than a raw loss number, and `not yet` is an honest answer.
- Log scale for both the learning-rate slider and the loss chart: the interesting values span several orders of magnitude.
- Pure Python, no NumPy: 120 points train in milliseconds and every line of the algorithm is readable.

## Limitations
One input feature and a straight line only; plain batch gradient descent (no momentum, mini-batches or adaptive rates such as Adam); synthetic data; the 1% rule and the 400-step budget are my choices; the divergence threshold depends on the data's scale, so the exact "safe" rates are specific to this dataset.
