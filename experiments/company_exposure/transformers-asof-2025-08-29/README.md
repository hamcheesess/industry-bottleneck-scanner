# Fixed-case historical hypothesis exercise

Information cutoff: 2025-08-29 20:00 UTC / 16:00 America/New_York.
Preparation date: 2026-09-07. Topic fixed by user, not a blind historical backtest.
No later actuals, restatements, M&A events or persistence counts justify the thesis.
Forecasts published before the cutoff may legitimately address future periods.

`report-source.md` is the Korean canonical source. `information-set.json` records
eight original source versions and reviewed availability bounds; the validator
checks metadata, not the independent authenticity of historical publication.
`market-origin.json` contains only pre-cutoff market assessment dates and hashes.
`research-audit.json` separates calculations, excluded leads, and unresolved inputs.

```bash
PYTHONPATH=src python experiments/company_exposure/transformers-asof-2025-08-29/build_review.py --market-dir /path/to/original/calibration/output
python experiments/company_exposure/multi-company-2026-09-06/render_report.py --source experiments/company_exposure/transformers-asof-2025-08-29/report-source.md --display-date '정보 기준 2025.08.29' --font-dir /path/to/nanum-fonts --output /path/to/report.pdf
```

The adapted table of contents and LLM/code division are documented in
`docs/adaptive-investment-report-contract.md`. Required questions are stable;
chapters, national comparisons and company counts are not rigid gates.

Important original-period observations: Arcosa backlog USD450m, +9% YTD, but
utility-related sales -2% on lower steel prices; AEP contracted incremental load
24GW; GEV original Electrification revenue USD2201m / EBITDA322m / 14.6%; Siemens
Grid profit before special items EUR448m / margin15.9%. None is a product-level
cash-flow or undervaluation conclusion. Later comparative columns are excluded.

The report establishes bounded hypotheses and research priorities. The other four
trigger constituents' causes, product-level deficits, company FCF, historical
market expectations and nine numerical scenarios remain unresolved. This is
`not_evaluable_missing_data`, not a failed return screen. No final DB publication,
historical registry mutation or numeric investment threshold change occurred.

Seven meaningful regression tests cover future actuals, later restatements,
same-day uncertainty, forecast horizons, IDs, timezones and non-approval semantics.
