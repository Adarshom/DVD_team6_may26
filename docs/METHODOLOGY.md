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
