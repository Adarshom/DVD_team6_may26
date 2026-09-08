# Verification record

## Passed

- All 11 supplied CSV files inspected; raw row counts and SHA-256 hashes recorded.
- One row per order and per order-item pair verified.
- Orders and item rows preserved through preparation.
- Item-based gross value reconciles to order totals; independently aggregated payments reconcile to the source payment file.
- Multi-seller and multi-category value allocation tested without full-order duplication.
- Missing reviews and unobserved delivery outcomes excluded from the appropriate denominators.
- Calendar-day promise adherence checked, including same-day delivery.
- Nonnegative valid journey durations and kilometre distance units checked.
- Delivered-customer history distinguishes repeat orders from repeat buyers.
- Marketing lead/win/seller matching counts checked; 90-day value independently reconciled to acquired-sales records.
- Every one of the 10 final and 33 detailed question builders executed and produced serializable Plotly figures.
- Empty, sparse and canceled-order selections exercised.
- Combined category, state and date selections reconciled against source item rows.
- Dash index, layout and dependency endpoints return HTTP 200.
- A real Flask/Dash POST callback with a filtered selection returns the correct category evidence.
- Evidence CSV content and reset defaults checked.
- Genuine Dash frontend visually inspected against recorded Flask callback responses. The visual check caught and resolved zero-height responsive graphs. Heatmap polarity and ordered value/delay bins were corrected.

Run `python -m unittest discover -s tests -v` to reproduce the **11 test methods**, including their many question and edge-case subtests. The captured run is in `docs/test-results.txt`.

## Limits of verification

- The available supervised browser environment does not contain the Python runtime. The frontend rendering check used the real Dash JavaScript/CSS, actual layout/dependency responses and captured genuine Python callback responses. This is a visual check, **not a completed live browser-to-Python end-to-end test**.
- Filtering, CSV generation and reset logic were exercised through Python and HTTP callback tests; not every dropdown combination was manually clicked in a live Python-hosted browser.
- Desktop layout was visually inspected. Mobile media rules are included, but a device/mobile browser session was not verified.
- Docker and production hosting configurations are provided but were not deployed or container-built here.
- Portuguese review-text sentiment is intentionally not implemented. Star sentiment is a clearly named rating proxy.
- The presentation deliverable included here is an outline, not a finished PowerPoint deck.

No mock data is used in the application. The temporary rendering harness is not included in the deliverable and is not part of the application runtime.
