# Technical report

## A Visual Study of E-Commerce Orders, Delivery & Customer Satisfaction

**DVD 2026 T2 · Group 6**

## Decision and scope

Grow the marketplace while protecting the customer experience. The dashboard identifies where observed transaction value and poor service overlap, where seller dependence creates exposure, and which acquisition outcomes can be verified from linked data.

This report uses the default dashboard cohort: all delivered orders in the supplied historical extract, minimum 30 observations per segment where applicable, and low ratings defined as 1–2 stars. Marketing analyses use all supplied leads. No external data or synthetic observations are used.

## Executive findings

- **R$15.42m in gross order value across 96,478 delivered orders.** Gross value includes freight; it is not marketplace net revenue.

- **Average review 4.16/5** across 95,832 reviewed orders. The low-rating share is 12.8%.

- **Late deliveries have a 62.4% low-rating share, versus 9.3% for deliveries meeting the promised date.** The large association supports investigating promise failures; it does not prove they caused every poor review.

- **The top 10% of sellers (297 of 2,970) account for 66.3% of selected value. 11 eligible categories exceed HHI 2,500.** Concentration is value exposure, not a forecast of what would be lost.

- **344 matched sellers have a full 90-day observation window. Conversion speed versus 90-day value has Spearman ρ = -0.03.** The near-zero pooled correlation does not support optimizing sales-cycle speed alone.

## Priority actions

1. **Prevent broken delivery promises.** Instrument seller handoff and carrier exceptions; trial an alert before promised delivery is missed. Evaluate low-rating share and repeat purchasing, with gross value and catalogue coverage as guardrails.

2. **Focus category fixes on economic weight.** Start with high-value categories that exceed the selected-market low-rating benchmark. Watches Gifts, Bed Bath Table, Computers Accessories and Furniture Decor are substantial examples. Diagnose seller, lane and listing contributions before restricting sellers.

3. **Reduce concentrated supply risk.** Identify backup sellers in categories over the workbook HHI screen, especially where top sellers also show service problems. Treat the underperformance control as a sensitivity scenario with no replacement sales, not a prediction.

4. **Recruit supply selectively.** The category–state view surfaces observed demand alongside thin local trading supply. Validate transport economics and addressable demand before claiming an expansion opportunity.

5. **Measure seller quality after acquisition.** Compare equal-age seller cohorts on observed value, reviews and delivery reliability. Improve source attribution and qualification data before making channel budget decisions.

## Answers to the ten final questions

### Q1. How much revenue comes from repeat customers, and what experience factors distinguish repeat buyers from one-time buyers?

Repeat buyers account for 5.6% of selected gross value. These are customers with 2+ delivered orders in the full observed history.

**Charts:** Who contributes value?; Experience comparison · row-normalized colours; First delivery experience and observed 90-day return.

**Interpretation:** Repeat buyer includes their first order; is_repeat marks only second and later delivered orders. Heatmap hover shows original units; late rate and freight burden are percentages. Return chart uses only first purchases with 90 days of follow-up. It does not prove what causes retention.

**Suggested action:** Protect first-order delivery reliability; validate retention interventions with a controlled experiment.

**Evidence:** `docs/evidence/Q01.csv`. Values change with dashboard filters.

### Q2. At what delivery delay does customer satisfaction drop sharply, and does the tipping point differ by category or customer state?

The largest adjacent-bin rating drop is 1.19 stars on entering (3.0, 7.0] days relative to the promise.

**Charts:** Satisfaction as the promise is missed · 95% mean CI; Does the pattern differ by category?; Does the pattern differ by customer state?.

**Interpretation:** Bins use calendar-day lateness; 0 means delivered on the promised date. The largest adjacent-bin drop is descriptive and depends on binning, sample size and category mix, not a validated causal threshold. Heatmaps show the highest-volume 18 rows.

**Suggested action:** Escalate delivery exceptions before the promise is missed, then test category-specific alert thresholds.

**Evidence:** `docs/evidence/Q02.csv`. Values change with dashboard filters.

### Q3. Where is customer demand strong but seller supply thin, and which category × state combinations should the marketplace prioritize for growth?

90 category–state combinations have at least 30 orders and no observed active seller in the same state.

**Charts:** Demand pressure · orders / (local sellers + 1); Demand versus active local sellers.

**Interpretation:** Supply means sellers observed trading in the period and category, across all buyer states. Heatmap uses orders / (local sellers + 1), a smoothed descriptive ranking that keeps zero-supply cells visible; exact counts are in the table. Zero observed supply is not proof of an unserved market. Demand reflects transactions, not latent demand. Other filters still constrain supply.

**Suggested action:** Prioritize seller recruitment where observed demand is substantial and local fulfilment is scarce; validate logistics economics before expanding.

**Evidence:** `docs/evidence/Q03.csv`. Values change with dashboard filters.

### Q4. How do delivery distance, freight burden and delivery performance trade off, and where are customers paying high freight without receiving better service?

45 eligible lanes have both above-median freight burden and above-median delivery time in this selection.

**Charts:** Cost versus service · each bubble is a lane; Distance versus freight burden; Delivery time across distance bands · 95% mean CI.

**Interpretation:** Lane distance is the average straight-line seller-to-customer ZIP distance. Freight burden = freight / merchandise value. R$/km excludes distances below 1 km. No carrier costs, subsidies, cart events or promised service tiers are supplied.

**Suggested action:** Audit expensive, slow lanes by carrier and product mix. Freight paid alone cannot establish logistics profitability or fairness.

**Evidence:** `docs/evidence/Q04.csv`. Values change with dashboard filters.

### Q5. Which categories generate high revenue but disproportionately poor customer satisfaction, and how much marketplace revenue is exposed?

R$7.06m (45.8%) sits in 14 high-value categories with above-benchmark low-rating shares.

**Charts:** Where value and experience conflict; Category value concentration.

**Interpretation:** High value = at or above eligible-category median (R$66.4k); poor satisfaction = above the selection’s 12.8% low-rating share. Exposure is selected gross value, not predicted lost revenue. Review threshold follows the filter.

**Suggested action:** Fix service in economically significant categories before reducing catalogue breadth. Protect high-value categories with healthy satisfaction.

**Evidence:** `docs/evidence/Q05.csv`. Values change with dashboard filters.

### Q6. How dependent is marketplace revenue on a small group of sellers, and which categories are most exposed if top sellers underperform or leave?

The top 10% of sellers (297 of 2,970) account for 66.3% of selected value. 11 eligible categories exceed HHI 2,500.

**Charts:** How concentrated is seller value?; Category seller concentration · HHI; Category concentration heatmap.

**Interpretation:** Seller value is the sum of that seller’s items and freight, never the full value of a shared order. HHI = 10,000 × sum of squared seller value shares. The 2,500 threshold follows the workbook as a descriptive risk screen, not a regulatory conclusion.

**Suggested action:** Develop backup supply in concentrated categories; account for replacement demand before interpreting exposure as lost revenue.

**Evidence:** `docs/evidence/Q06.csv`. Values change with dashboard filters.

### Q7. Which marketing lead sources generate the highest conversion from marketing-qualified lead to closed seller?

842 of 8,000 leads converted (10.5%). Paid Search has the highest point estimate among named eligible sources: 12.3% (195/1586).

**Charts:** From lead to observed seller; Source conversion · 95% Wilson CI.

**Interpretation:** Lead cohort is filtered by first-contact date. Closed outcomes use all supplied won dates, so newer leads may have less follow-up. Unknown is not a named channel; it remains in totals and the chart. Confidence intervals may overlap, so the highest point estimate does not establish a reliably superior source. Matched means seller_id exists in e-commerce items; it is not a full-business activation rate.

**Suggested action:** Use conversion and uncertainty alongside downstream trading quality before moving acquisition budget. Marketing spend and CAC are unavailable.

**Evidence:** `docs/evidence/Q07.csv`. Values change with dashboard filters.

### Q8. Do different marketing channels bring commercially stronger sellers, not just more sellers?

Only 45 of 842 closed sellers report positive monthly revenue. Commercial strength cannot be ranked reliably from declarations alone.

**Charts:** Declared scale · positive values only; Matched mature sellers · median first-90-day performance; Business profile of closed sellers; Catalogue-size declarations · sparse coverage.

**Interpretation:** Zero revenue declarations are retained in source data but excluded from this positive-only plot; they are not assumed to be real zero businesses. Downstream chart requires 5 matched sellers per source and a full 90-day observation window. Results exclude unmatched sellers; source-level seller counts are shown.

**Suggested action:** Improve seller qualification data, then compare equal-age seller cohorts rather than raw totals or self-reported revenue.

**Evidence:** `docs/evidence/Q08.csv`. Values change with dashboard filters.

### Q9. Does faster lead conversion translate into stronger seller performance and better customer experience after sellers join the marketplace?

344 matched sellers have a full 90-day observation window. Conversion speed versus 90-day value has Spearman ρ = -0.03.

**Charts:** Conversion speed versus observed value; Equal-age cohort comparison; Conversion speed versus customer experience.

**Interpretation:** Only delivered orders purchased from won_date through day 89 are counted. Pre-win orders are excluded. Unmatched sellers are not labelled organic. Ratings in the cohort table are seller-weighted; CX scatter requires 5 reviews per seller. Correlation is unadjusted and does not establish predictive or causal value.

**Suggested action:** Do not optimize sales-cycle speed alone. Track seller activation, equal-age trading value and customer outcomes together.

**Evidence:** `docs/evidence/Q09.csv`. Values change with dashboard filters.

### Q10. Do high-value orders receive better or worse service, and where is the experience gap largest across categories?

R$600+ orders average 4.00/5, versus 4.20/5 below R$150.

**Charts:** Delivery distributions by full order value; Experience gaps across categories; Installments and order value.

**Interpretation:** Value bands use the entire order, even under an item/category selection; aggregate value elsewhere attributes only selected items. Processing fees and margins are absent. No claim is made about installment profitability.

**Suggested action:** Check high-value service gaps within categories before designing a premium-order service policy.

**Evidence:** `docs/evidence/Q10.csv`. Values change with dashboard filters.

## Preparation and analytical method

### Read the measures correctly

The default cohort is **delivered orders**, over the full supplied purchase-date range. Clearing the status filter includes every status. This is a historical extract, not a live marketplace feed. Partial edge months should not be interpreted as growth or decline.

| Measure | Definition and denominator |
| :--- | :--- |
| Gross order value | Sum of selected item price + freight. BRL throughout. This is transaction value, not marketplace commission, profit, or net revenue. |
| Orders | Unique order IDs in the selection. Item filters select orders containing matching items. |
| Average review | Mean of the latest answered star rating per order; unreviewed orders are excluded. |
| Low-rating share | Reviewed orders at or below the chosen star threshold / reviewed orders. Default threshold: 2. |
| Late-delivery share | Delivered orders arriving after the promised calendar date / delivered orders with valid observed delivery duration and promise dates. |
| Full order value band | Price + freight for the complete order, including items outside a selected category. |
| Repeat buyer | Customer unique ID with at least two delivered orders in the entire observed extract. Includes that buyer's first order. |
| Repeat order | Second or later delivered order for the same customer unique ID. This differs from repeat-buyer revenue. |
| Lifetime value | Sum of observed delivered-order values. The extract does not cover a customer's true lifetime. |
| Freight burden | Freight / merchandise value. Aggregate charts use ratio of sums; item distributions use per-item ratios. |
| Seller value | Sum of a seller's own item price + freight. A shared order's full value is never credited to every seller. |
| HHI | 10,000 × sum of squared seller value shares within a category. The workbook's >2,500 rule is a descriptive concentration screen. |
| Observed harm | A late delivery OR a low rating. Count once per order within each displayed segment. |

### How the tables join

1. `orders.customer_id → customers.customer_id` is many-to-one in concept and one-to-one in this extract. `customer_unique_id` identifies the customer across orders. It is **not** a unique key in the customers table.
2. Aggregate payments by `order_id` before joining orders. Sum payment value, retain all payment types, and take the maximum installment count. The payment-type filter matches any type used.
3. Sort reviews by answer timestamp, creation date and review ID. Retain the latest answered review per `order_id`. A review ID is not globally unique in the supplied extract.
4. Join items to products by `product_id`, categories by Portuguese category name, and sellers by `seller_id`. Keep every item at `(order_id, order_item_id)` grain.
5. Deduplicate geolocation rows, reject coordinates outside broad Brazil bounds, and take the median coordinate for each five-digit ZIP prefix. Join customer and seller coordinates independently.
6. Join marketing leads to closed deals by `mql_id`, then link the resulting closed seller to item sales by `seller_id`. Preserve all leads for conversion denominators, including those without a closed deal.

Orders, items and marketing are stored separately. Charts aggregate value from items, but compute order outcomes from distinct order IDs within each segment. Counts across categories, sellers and lanes may overlap when an order has multiple items or sellers. **Do not sum segment counts to obtain unique marketplace orders.**

### Corrections to the workbook definitions

- `delivery_time` is delivery timestamp minus purchase timestamp. The Variables sheet writes the subtraction in reverse.
- `delivery_estimate_mismatch` preserves the timestamp difference in days. Promise adherence uses the derived `delay_days` calendar-date difference, so a delivery on the promised day is not marked late merely because the promise is recorded at midnight.
- `approval_time` is approval minus purchase; `processing_time` is carrier handoff minus approval. Negative durations are excluded from duration charts and logged, not silently turned into positive values.
- `distance` uses the Haversine great-circle distance in kilometres, not Euclidean degrees. It is a straight-line proxy between median ZIP coordinates, not a road route.
- `freight_per_distance` excludes distances below 1 km to avoid unstable divisions. At order grain, distance is the mean over distinct seller routes. At item grain, it is that seller's route.
- Text sentiment is **not fabricated**. The app shows a clearly named star-based `rating_sentiment` proxy and written-comment presence. Validated Portuguese review-text sentiment remains unimplemented.
- Seller revenue shares, top-percentile concentration and category HHI are calculated from the selected item values. Full order totals are never duplicated across sellers. Top 10% uses the ceiling of 10% of active sellers, ranked by value.

### Filters and chart interpretation

Purchase dates, category, customer state, seller state, seller ID, status, payment type, delivery outcome and full order value apply to commerce pages. Changing filters recomputes charts, KPI denominators, findings and evidence downloads. Clearing a multi-select means all values. Reset restores delivered orders and the full date range.

The minimum sample applies to the segment's relevant count: reviews for satisfaction comparisons, observed deliveries for late-rate comparisons, and orders for demand or value. Marketing conversion uses a separate minimum lead count. Seller-quality source comparisons require five mature matched sellers; the acquisition CX scatter requires five reviews per seller. Some exact-total charts and distributions intentionally retain all observations. Tables expose counts for review.

The demand/local-supply view counts active local sellers across all buyer destinations while retaining other selections. A state with no observed local seller may still receive nationwide deliveries. It is not proof of unserved demand. Most heatmaps display at most 18 high-volume rows for legibility; evidence tables retain all eligible rows.

Chart toolbars support zoom, pan, reset and PNG export. Click legend entries to hide or isolate series. Use treemap branches for drilldown. Chart-point clicks do not change the global filters. Evidence tables support sorting, searching and a filtered-result CSV download. The download uses the global filter result, not additional search text typed into the table.

### Marketing and observation windows

Marketing pages use **first-contact dates and lead source**, independently of commerce controls. Their conversion measure is observed wins / leads in the selected contact cohort, using all supplied closed-deal outcomes. Follow-up differs by contact date; source conversion is not a causal channel effect or CAC.

Only 380 of the 842 closed sellers match e-commerce item sales. Absence from this extract does not prove non-activation. Unmatched sellers must not be called organic sellers.

Seller comparisons use delivered purchases at or after `won_date` and before `won_date + 90 days`. A mature cohort must have 90 days before the latest observed delivered purchase, 29 August 2018. This is an observation-window proxy, not a guarantee that all seller activity is captured. Positive-only revenue declaration plots exclude 797 zero declarations, while retaining those source values. Only 69 closed sellers have a declared catalogue size.

Repeat-purchase comparisons use first delivered purchases with at least 90 days of observed follow-up. Seller ramp plots use the first sale within the selection, not a known acquisition date; unreached volume thresholds remain visible in evidence tables.

### What the data cannot establish

The files do not include marketplace fees, margins, carrier costs, cart/session events, refunds, true churn, competitor supply, or reliable acquisition data for unmatched sellers. Consequently, the dashboard cannot determine cart conversion, freight subsidies, installment profitability, causal satisfaction drivers, true lifetime value or revenue that will actually be lost.

The delivery tipping point is the largest adjacent-bin decrease in average rating among eligible bins, not a validated causal threshold. Error bars are approximate 95% confidence intervals for means; lead conversion uses Wilson binomial intervals. Item-weighted product charts can contain shared-order outcomes, so their intervals do not account for clustering. Correlations are descriptive and unadjusted. Recommendations are priorities for investigation or experimentation.

### Workbook coverage

All **10 final questions** and all **33 populated detailed questions** are implemented. The detailed sheet is named “35 Questions in detail by ind c” but contains 33 question rows. The unrelated fourth sheet is not used as a requirements source. Older detailed-sheet notes saying marketing data is absent are superseded where the supplied funnel files can actually be linked. The original question text is retained in `docs/questions.json` and displayed in the app.


## Visualization rationale

- Time series separate growth/value from customer outcomes without combining incompatible units on one axis.

- Stacked rating distributions expose the whole experience mix rather than relying only on average stars.

- Binned lines and confidence intervals reveal nonlinear delivery patterns while exposing sample uncertainty.

- Heatmaps reveal category, state and delivery interactions; sparse cells are suppressed.

- Bubble plots combine scale and service measures to prioritize economically relevant segments.

- Pareto curves and HHI quantify dependence without confusing large sellers with bad sellers.

- Box plots show distributions; large plots transmit exact summary quartiles rather than raw point arrays.

- Funnel counts and Wilson intervals retain conversion denominators. Equal-age seller windows reduce exposure-time bias.

## Reproducibility and validation

Run `python prepare_data.py`, `python build_report.py`, and `python -m unittest discover -s tests -v`. Source hashes and reconciliations are stored in `data/processed/quality.json`. See `docs/QA.md` for what was and was not verified.

The Python framework was selected because pandas supports transparent relational preparation, Plotly supplies interactive statistical charts, and Dash connects those charts to Python callbacks without a separate JavaScript business-logic layer. Parquet reduces startup and disk costs. No hosted database, paid API, or API key is required.

Framework reference: [Official Plotly Dash callback documentation](https://dash.plotly.com/basic-callbacks).

## Remaining evidence gaps

Validated Portuguese text sentiment is not implemented. The supplied stars and written-comment presence are used honestly as separate measures. A later NLP extension should use a suitable Portuguese model and manually validated labels, with review-level accuracy and bias checks.

Future research should control for category, region, seasonality and order value, distinguish seller and carrier responsibility, and use experiments to evaluate whether interventions improve satisfaction without harming growth. Missing margins, fees, browsing events and carrier costs must be acquired before making profitability or cart-conversion claims.