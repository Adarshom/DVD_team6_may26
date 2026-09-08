# Marketplace Observatory

**A Visual Study of E-Commerce Orders, Delivery & Customer Satisfaction**  
DVD 2026 T2 · Group 6

A working **Python Plotly Dash application** built from the supplied Excel question workbook and all eleven CSV files. No API keys or external data services are needed. Charts and filters run against the included local data.

## Start the application

Use **Python 3.11 or 3.12**. Extract the ZIP, open a terminal in the `marketplace_dash` folder, then run:

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

Install and start:

```bash
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8050** in your browser. Keep the terminal open. Stop with Ctrl+C. The included prepared tables make first startup quick; if they are absent, the application rebuilds them automatically from the bundled source CSVs.

## What is included

- Executive overview with value, orders, reviews, delivery reliability and low ratings.
- Ten final-question pages, each with interactive charts, findings, supporting tables, scope notes and actions.
- Detailed-question lab covering **all 33 populated rows** in the sheet titled “35 Questions in detail by ind c”.
- Commerce filters: date, category, customer state, seller state, seller ID, order status, payment type, delivery outcome and full-order value band.
- Controls for low-rating definition, minimum observations, top sellers / seller ramp target, and seller underperformance scenarios.
- Separate lead-cohort dates, lead source and minimum-lead controls on marketing pages.
- Plot zoom, pan, legend interactions, PNG export, treemap drilldown, searchable/sortable evidence tables and CSV downloads.
- A methodology page with metric definitions, workbook corrections and data-quality checks.
- Reproducible data preparation, tests, technical findings and a presentation story outline.

## Project files

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
| `docs/PRESENTATION_OUTLINE.md` | Suggested seven-slide narrative for the course presentation |
| `docs/QA.md` | Verification scope and results |
| `tests/test_project.py` | Meaningful grain, metric, filter, chart and callback checks |

## Reproduce the analysis

```bash
python prepare_data.py
python build_report.py
python -m unittest discover -s tests -v
```

The raw CSVs are unchanged. Data preparation retains all orders and item rows. Invalid stage durations are excluded only from duration measures. Missing ratings do not enter rating denominators. Missing delivery outcomes do not enter late-delivery denominators.

## Important interpretation rules

1. “Gross order value” includes freight. It is not marketplace net revenue or profit.
2. The default is delivered orders. Item-level category/seller filters attribute only selected item value, while full order value bands use the complete order.
3. One-star/low-rating counts across sellers or categories may overlap because some orders involve multiple sellers or categories.
4. Marketing pages use independent lead filters. Only 380 of 842 closed sellers match the sales extract. Unknown or unmatched acquisition sources are not labelled organic.
5. The workbook's reversed delivery duration and Euclidean-degree distance are corrected and documented. Star-based sentiment is labelled as a rating proxy; Portuguese text sentiment is not claimed.
6. Findings describe observational associations. Cart conversion, carrier economics, processing fees, causal effects and true churn cannot be measured from these files.

## Hosting

This app needs a **persistent Python web process** with its bundled Parquet files. It is not a static website or a Cloudflare Worker app. For a Linux Python/container host:

```bash
gunicorn app:server --bind 0.0.0.0:8050 --workers 1 --threads 4 --timeout 120
```

The included Dockerfile is an alternative. A machine with approximately 2 GB of memory is a sensible starting point for the loaded tables and concurrent chart calculations. No deployment or public sharing has been performed. Do not expose the Flask development server publicly; use the production command above.

## Verification status

See `docs/QA.md`. Source reconciliation, filter logic, all question figure builders, empty/sparse cases, HTTP callback responses, CSV export and reset behaviour were checked. The Dash frontend was visually inspected using genuine captured server responses because the browser preview environment cannot execute Python. A live browser-to-Python session and deployment were not tested in this environment.

Framework reference: [Official Dash callback documentation](https://dash.plotly.com/basic-callbacks).
