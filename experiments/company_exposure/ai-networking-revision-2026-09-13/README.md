# AI networking historical report — September 13 revision

Information cutoff: **2025-06-30T20:00:00Z**. Written September 13, 2026. Retrospective user-selected case; first stored passing month-end observation is not a daily-first or outcome-blind discovery claim.

Read `report-ko.pdf`. This is a screen-grade research benchmark, **not trade approval**. Narrative structure is flexible; economic understanding, evidence, cash conversion, valuation, downstream research and 6–18 month scenarios remain required coverage.

## Reproduce

Python 3 with reportlab and NanumGothic Regular/Bold fonts:

```sh
python model.py
python assemble_report.py
python render_report.py --font-dir /path/to/fonts --source report-ko.md --output report-ko.pdf
```

`model.py` uses only committed inputs, with no provider or model calls. The first year is an explicit FCFF cash bridge; later years use incremental sales/capital. Every growth, margin, tax, capital-intensity, discount-rate and terminal return assumption remains a research assumption. No probability-weighted target price is claimed.

`evidence-ledger.json` covers core financial facts and input groups. `meta-facts.json` preserves the customer source recheck. `historical-prices.json` preserves the retrieved historical close responses. `selection.json` preserves prior input hashes and explicitly replaces the legacy fixed-outline instruction without rewriting the historical record. `review-record.json` records scope, stops, limitations and validation.

Important limitations: COHR preferred claims use book value and assumed non-cash accretion, with conversion/payment options unmodeled; quarter-average diluted shares and latest-quarter annualized revenues are proxies; product-level FCF is not publicly measured here; LITE is operating corroboration, not a completed valuation. Base-only constant-multiple prices are mechanical diagnostics, separate from DCF full-recognition prices.

The reusable learning is the **claim → operating mechanism → financial assumption → price implication → falsifier** chain, not a fixed chapter count or a requirement that each report produce a buy.
