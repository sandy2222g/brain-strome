# Appliance Power Cost

![demo](docs/demo.png)

## Problem
Electricity with peak and off-peak rates makes "what does this appliance cost me?" hard to answer, and a single flat-rate estimate hides when you could save.

## Solution
For each appliance, compute monthly kWh (watts x hours x days) and cost at the peak and off-peak rates by its share of peak use, then show the saving if shiftable loads (dishwasher, washing machine, EV charger) ran entirely off-peak. Sample (invented home and tariff, 30 days): total 146.42, of which the EV charger is 75.60; running the three shiftable loads off-peak saves 43.32. A single flat rate would say 140.70 and miss which appliances are worth moving.

## Architecture
```mermaid
flowchart LR
  UI[static page] -->|POST /report| API[FastAPI api.py]
  API --> Core[core.py: kwh_per_month, cost, report]
  Core --> Data[data/home.json]
```

## Setup
```bash
pip install -r requirements-dev.txt
PYTHONPATH=src uvicorn powercost.api:app --port 8000
PYTHONPATH=src pytest
docker build -t powercost . && docker run -p 8000:8000 powercost
```
Deploy: see [DEPLOY.md](DEPLOY.md) (Render or Hugging Face Spaces).

## Design decisions
- Peak share per appliance (0-1): captures time-of-use without needing an hourly profile.
- Only appliances marked `shiftable` are moved: a fridge cannot wait for the night.
- Flat-rate cost shown alongside: makes the value of time-of-use pricing visible.
- Money rounded to cents per appliance: matches how a bill is read; totals are sums of rounded rows.

## Limitations
- Constant wattage; real appliances cycle (a fridge compressor, an oven element).
- No standing charges, taxes or tiered rates.
- Appliances and tariff are invented.

Data: invented, MIT licence.
