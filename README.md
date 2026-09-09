# Marketplace Observatory

This is a Python Plotly Dash application for visualizing e-commerce orders, delivery data, and customer satisfaction. It is built from the supplied Excel workbook and CSV files. No external APIs or services are needed. Everything runs locally on the provided data.

## Setup Instructions

You need Python 3.11 or 3.12. Open a terminal in the `marketplace_dash` folder and create a virtual environment.

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install the dependencies and start the app:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8050 in your browser. Leave the terminal open while you use the app. Press Ctrl+C to stop it. The app loads fast if the prepared tables are present. If they are missing, it will build them from the CSVs automatically.

## Project Files

| File | Purpose |
| :--- | :--- |
| `app.py` | Dash layout, controls, callbacks and CSV download |
| `analytics.py` | Shared filters, metrics and every chart/question implementation |
| `prepare_data.py` | Read raw CSVs, validate joins and produce prepared tables |
| `build_report.py` | Regenerate findings, question coverage and default evidence tables |
| `assets/style.css` | Responsive visual design |
| `data/raw/` | All eleven original CSVs and the supplied workbook |
| `data/processed/` | Order, item, marketing and acquired-sales Parquet tables; quality JSON |
| `docs/TECHNICAL_REPORT.md` | Findings, recommendations, limitations and methodology |
| `docs/METHODOLOGY.md` | Definitions shown inside the dashboard |
| `docs/QUESTION_COVERAGE.csv` | Every supplied final and detailed question mapped to its view |
| `docs/questions.json` | Exact question wording extracted from the workbook |
| `docs/evidence/` | Default-filter evidence for the ten final questions |
| `docs/PRESENTATION_OUTLINE.md` | Suggested narrative for the course presentation |
| `docs/QA.md` | Verification scope and results |
| `tests/test_project.py` | Grain, metric, filter, chart and callback checks |

## Reproduce the Analysis

Run these commands to rebuild the data tables and reports from scratch.

```bash
python prepare_data.py
python build_report.py
python -m unittest discover -s tests -v
```

The raw CSV files are never modified. The preparation steps keep all order and item rows. Invalid times are left out of duration calculations. Missing reviews do not affect review averages. Missing delivery updates do not affect delivery calculations.

## Interpretation Rules

1. Gross order value includes shipping costs. It is not marketplace revenue.
2. The default view shows delivered orders. Category and seller filters only apply to their specific items. Value bands look at the entire order.
3. Order totals can overlap. An order with items from multiple sellers or categories counts for all of them.
4. Marketing pages have their own filters. Only 380 out of 842 closed sellers are present in the sales data. Unknown sources are not grouped with organic leads.
5. Corrections to the workbook logic are documented. Star ratings measure sentiment directly. We do not use unverified Portuguese text processing.
6. These findings show associations, not causes. We do not have the data to measure conversion rates, carrier costs, or causal relationships.

## Hosting

Run the application using a persistent Python web server. Do not use the Flask development server in production.

For a Linux environment with containers:

```bash
gunicorn app:server --bind 0.0.0.0:8050 --workers 1 --threads 4 --timeout 120
```

You can also use the included Dockerfile. We recommend at least 2 GB of memory to hold the data tables and generate charts.

Framework reference: [Official Dash callback documentation](https://dash.plotly.com/basic-callbacks).
