# 2026-09-06 multi-company comparison checkpoint

This package completes a Korean comparison of seven manufacturers/adjacent
companies in one industry path. It does not claim completion of the whole
industry universe, company valuation, or nine quantitative investment scenarios.
It is research-only; the existing exposure reviewer refuses historical reuse and
returns `publication_eligible=false` for all seven companies.

## Reproduction

From repository root, with the original calibration run 32717734277 extracted:

```bash
PYTHONPATH=src python experiments/company_exposure/multi-company-2026-09-06/build_inputs.py --market-dir /path/to/calibration/output
python experiments/company_exposure/multi-company-2026-09-06/render_report.py --font-dir /path/to/nanum-fonts --output /path/to/power-grid-multi-company-research-ko-20260906.pdf
```

The renderer requires ReportLab and `NanumGothic-Regular.ttf` /
`NanumGothic-Bold.ttf`; fonts and issuer PDFs are not redistributed. The canonical
Korean prose lives in `report-source.md`. Inputs and calculations require no model
or provider calls. Source publication precision and current retrieval are explicit;
current pages do not become historical snapshots merely because they show older
publication dates. Original market files are hashed in the extract.

Key new findings: the first sampled market trigger was 2025-08-29, not the August
2026 follow-up; relative breadth and proximity to highs passed, volume breadth did
not. GEV acquisition effects and working-capital inflows require separation.
Siemens and Korean manufacturers show earnings conversion but disclose broader
scopes than LPTs. Hitachi construction is not production. AEP customer agreements
are not energized capacity, and the Texas audit is counterevidence for near-term
timing. Arcosa's pending transaction confounds a pure bottleneck equity thesis.

## Next executable research

1. Reconcile product-level orders/shipments, facility qualification and actual
   ramp, ASPs and operating-cost bridges for the four direct listed comparators.
2. Freeze same-date security prices, share counts, net debt and independent
   market expectations. Foreign names remain supply comparators until the
   security-level research universe is explicitly defined.
3. Populate downside/base/upside by 6/12/18 months using reviewed evidence; never
   use segment margins as transformer margins or issuer guidance as consensus.
4. Run existing financial/publication gates before final DB publication. No DB
   write or site change occurred in this checkpoint.

Validation performed: original-input extraction and seven-company exposure gate;
11 existing exposure/cash-quality unit tests; PDF text and rendered-page review.
Token totals are unavailable, recorded as null rather than estimated. Full-suite
CI is tracked on the resulting remote commit separately.
