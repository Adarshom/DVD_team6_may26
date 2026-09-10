"""Generate source-backed findings and workbook-to-implementation traceability."""
from pathlib import Path
import json
import pandas as pd
from analytics import load,filter_data,final_question,overview,ROOT,money,pct


# Generate all evidence files, technical report, and presentation outline.
#Markdown files are used because they are human-readable, version-controllable, and can be converted to PDF or slides with pandoc or similar tools.
def build():
    o,i,m=load();o,f=filter_data(o,i,statuses=['delivered'])
    questions=json.loads((ROOT/'docs/questions.json').read_text(encoding='utf-8'))
    docs=ROOT/'docs';evidence=docs/'evidence';evidence.mkdir(exist_ok=True)
    results=[]
    for n in range(1,11):
        r=final_question(n,o,f,m)
        r['table'].to_csv(evidence/f'Q{n:02d}.csv',index=False)
        results.append(r)
    # Map every workbook question to its dashboard view. There are two - final 10 main questions and then additional 33 questions.
    coverage=[]
    for kind in ['final','detailed']:
        for q in questions[kind]:
            coverage.append({'sheet':'FINAL 10 QUESTIONS' if kind=='final' else '35 Questions in detail by ind c',
                'question_number':q['number'],'question':q['question'],
                'app_view':f'#q{q["number"]}' if kind=='final' else f'#lab → detailed question {q["number"]}',
                'code':f'analytics.py:{"final_question" if kind=="final" else "detail_question"}({q["number"]}, …)',
                'workbook_chart_request':q['charts'],'implementation_status':'Implemented with explicit data-limit notes'})
    pd.DataFrame(coverage).to_csv(docs/'QUESTION_COVERAGE.csv',index=False)
    lines=['# Technical report',
      '## A Visual Study of E-Commerce Orders, Delivery & Customer Satisfaction',
      '**DVD 2026 T2 · Group 6**',
      '## Decision and scope',
      'Grow the marketplace while protecting the customer experience. The dashboard identifies where observed transaction value and poor service overlap, where seller dependence creates exposure, and which acquisition outcomes can be verified from linked data.',
      'This report uses the default dashboard cohort: all delivered orders in the supplied historical extract, minimum 30 observations per segment where applicable, and low ratings defined as 1–2 stars. Marketing analyses use all supplied leads. No external data or synthetic observations are used.',
      '## Executive findings',
      f'- **{money(f.item_value.sum())} in gross order value across {len(o):,} delivered orders.** Gross value includes freight; it is not marketplace net revenue.',
      f'- **Average review {o.review_score.mean():.2f}/5** across {o.review_score.count():,} reviewed orders. The low-rating share is {pct(100*o.low_rating.mean())}.',
      f'- **{overview(o,f)["insight"]}** The large association supports investigating promise failures; it does not prove they caused every poor review.',
      f'- **{results[5]["insight"]}** Concentration is value exposure, not a forecast of what would be lost.',
      f'- **{results[8]["insight"]}** The near-zero pooled correlation does not support optimizing sales-cycle speed alone.',
      '## Priority actions',
      '1. **Prevent broken delivery promises.** Instrument seller handoff and carrier exceptions; trial an alert before promised delivery is missed. Evaluate low-rating share and repeat purchasing, with gross value and catalogue coverage as guardrails.',
      '2. **Focus category fixes on economic weight.** Start with high-value categories that exceed the selected-market low-rating benchmark. Watches Gifts, Bed Bath Table, Computers Accessories and Furniture Decor are substantial examples. Diagnose seller, lane and listing contributions before restricting sellers.',
      '3. **Reduce concentrated supply risk.** Identify backup sellers in categories over the workbook HHI screen, especially where top sellers also show service problems. Treat the underperformance control as a sensitivity scenario with no replacement sales, not a prediction.',
      '4. **Recruit supply selectively.** The category–state view surfaces observed demand alongside thin local trading supply. Validate transport economics and addressable demand before claiming an expansion opportunity.',
      '5. **Measure seller quality after acquisition.** Compare equal-age seller cohorts on observed value, reviews and delivery reliability. Improve source attribution and qualification data before making channel budget decisions.',
      '## Answers to the ten final questions']
    for q,r in zip(questions['final'],results):
        lines += [f'### Q{q["number"]}. {q["question"]}',r['insight'],
                  '**Charts:** '+ '; '.join(t for t,_ in r['charts'])+'.',
                  '**Interpretation:** '+r['note'], '**Suggested action:** '+r['action'],
                  f'**Evidence:** `docs/evidence/Q{q["number"]:02d}.csv`. Values change with dashboard filters.']
    lines += ['## Preparation and analytical method',(docs/'METHODOLOGY.md').read_text(encoding='utf-8'),
       '## Visualization rationale',
       '- Time series separate growth/value from customer outcomes without combining incompatible units on one axis.',
       '- Stacked rating distributions expose the whole experience mix rather than relying only on average stars.',
       '- Binned lines and confidence intervals reveal nonlinear delivery patterns while exposing sample uncertainty.',
       '- Heatmaps reveal category, state and delivery interactions; sparse cells are suppressed.',
       '- Bubble plots combine scale and service measures to prioritize economically relevant segments.',
       '- Pareto curves and HHI quantify dependence without confusing large sellers with bad sellers.',
       '- Box plots show distributions; large plots transmit exact summary quartiles rather than raw point arrays.',
       '- Funnel counts and Wilson intervals retain conversion denominators. Equal-age seller windows reduce exposure-time bias.',
       '## Reproducibility and validation',
       'Run `python prepare_data.py`, `python build_report.py`, and `python -m unittest discover -s tests -v`. Source hashes and reconciliations are stored in `data/processed/quality.json`. See `docs/QA.md` for what was and was not verified.',
       'The Python framework was selected because pandas supports transparent relational preparation, Plotly supplies interactive statistical charts, and Dash connects those charts to Python callbacks without a separate JavaScript business-logic layer. Parquet reduces startup and disk costs. No hosted database, paid API, or API key is required.',
       'Framework reference: [Official Plotly Dash callback documentation](https://dash.plotly.com/basic-callbacks).',
       '## Remaining evidence gaps',
       'Validated Portuguese text sentiment is not implemented. The supplied stars and written-comment presence are used honestly as separate measures. A later NLP extension should use a suitable Portuguese model and manually validated labels, with review-level accuracy and bias checks.',
       'Future research should control for category, region, seasonality and order value, distinguish seller and carrier responsibility, and use experiments to evaluate whether interventions improve satisfaction without harming growth. Missing margins, fees, browsing events and carrier costs must be acquired before making profitability or cart-conversion claims.']
    (docs/'TECHNICAL_REPORT.md').write_text('\n\n'.join(lines),encoding='utf-8')
    outline='''# Final presentation outline

1. **The leadership decision:** Grow marketplace value while protecting the customer experience. Introduce the order journey and the trade-off.
2. **Trust the model first:** Explain 11 relational source files, order versus item grain, latest review selection and the corrected delivery/distance definitions. Show default KPI cards.
3. **The broken promise:** Show Q2 and the early/on-time/late rating distribution. State the observed 4–7 day bin drop; explain that it is descriptive, not causal.
4. **Where a fix matters economically:** Show Q5 category value versus low-rating share. Name major categories and distinguish exposed value from predicted loss.
5. **Where to grow and where to diversify:** Show Q3 demand/local supply and Q6 concentration. Separate observed local supply from true market opportunity.
6. **Acquisition volume is not enough:** Show Q7 conversion and Q9 equal-age seller performance. Disclose the 380/842 match and 344 mature matched sellers, plus sparse declarations.
7. **Actions and measurement:** Propose a delivery-exception trial, targeted category fixes, backup supply, and equal-age acquisition quality tracking. Close with value and catalogue breadth as guardrails.

Demo path: Executive overview → Delivery tipping point → category and customer-state filters → Category priorities → Seller concentration → Lead conversion → Data and methodology.

Use the live app to export the selected chart PNGs and evidence CSVs. Exact claims and denominators are in TECHNICAL_REPORT.md. This file is a presentation outline, not a finished slide deck.
'''
    (docs/'PRESENTATION_OUTLINE.md').write_text(outline,encoding='utf-8')
    print('Wrote technical report, 43-question coverage map, ten evidence CSVs and presentation outline.')

#Standard Flashk app entry point
if __name__=='__main__':build()
