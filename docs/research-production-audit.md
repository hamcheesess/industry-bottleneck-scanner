# Repeatable investment research: implementation audit

As audited 2026-09-07, starting at fe41353e. This document is an implementation
inventory, not an assertion that end-to-end autonomous production is live.
The primary objective is repeated discovery, investigation and understandable
investment analysis of unfamiliar industries. A report is a test of this
system's output quality. Fixed questions; adaptable chapter structure.

| Component | Code / artifact | Actual status and boundary |
|---|---|---|
| Historical universe and market calibration | market_history.py; provider-free-market-calibration.yml | Historical Actions outputs exist; case report uses four dated trigger artifacts, not future persistence. Local raw history download is incomplete and is not reused as price proof. |
| SEC collection, normalized signals and bounded packets | SEC, operating and causal workflow files | Earlier production artifacts exist. Lexical matches are candidates, not semantic proof. |
| Causal research adjudication and state/edge gates | root-shock/edge/state/convergence workflows | Deterministic contracts and earlier executed artifacts; current 2025 report does not rewrite 2026 registries. |
| Source availability and forecast-vs-actual checks | research_information_set.py | Standalone helper used by build_review.py; validates entered metadata, not independent historical web authenticity. Not yet mandatory at every legacy ingestion boundary. |
| Company exposure and cash-flow quality | company_exposure.py; cash_flow_quality.py | Research helpers; require LLM/source interpretation. Do not certify product FCF. |
| Existing financial scenarios | bottleneck_financial_scenario.py | Calculates nine scenarios and FCF diagnostics, but equity value uses EV/operating-income multiple, NOT DCF. Requires supplied market expectations. FCF formula lacks an explicit D&A addback field; do not load reported EBIT/FCFF without reconciliation. |
| New cash-flow/price diagnostics | valuation_diagnostics.py; build_valuation.py | Reusable incremental FCFF and reverse equity cash-flow proxy sensitivities, tested and exercised in this report. Research-only, always publication_eligible=false. |
| Final-only publication and compact rejection | weekly_research_publish.py; web_contract/migrations | Export validation and database schema exist. No evidence of a deployed DB writer or scheduled complete weekly research run. |
| Website | separate industry-bottleneck-site repository | Existing reader site is not proof of live database-driven production or weekly refresh. This change does not deploy the revised report. |
| Korean narrative, new sources, competing hypotheses | source ledger and report source | LLM-authored/reviewed. Not converted into keyword-only judgments. |
| Token efficiency feedback | weekly publication policy / feedback schema | Recording contract exists; per-model actual input/output/cache-token telemetry is not yet an end-to-end measurement pipeline. No claimed savings percentage. |

## Hard rules versus tunable policy

Hard: exact information cutoff and publication version; no future actuals;
no unknown timestamp silently assumed before close; consistent currency,
period, product/entity scope and accounting basis; source independence;
missing data is not failed valuation; assumptions never relabeled as disclosures.

Policy: weekly cadence, 6/12/18-month investigation windows, 20% base-return,
-15% downside, 1.5 reward/downside and two catalysts. Existing rules remain;
they are provisional selection preferences, not empirically optimized facts.
Evaluate changes on multiple historically frozen cases with completeness held
constant; do not tune to make this transformer case pass.

## Production work still required

1. One research-job manifest connecting trigger, information set, claim ledger,
   financial model version, unresolved questions and publication decision.
2. Mandatory availability/version checks at every legacy boundary, not just the
   case script. Separate market observation time from retrieval/publication time.
3. Product-to-segment-to-group cash-flow reconciliation and original-vintage
   consensus when available; reverse valuations explicitly distinguish assumed
   expectations from observed consensus. Never add increments already in baseline.
4. Deterministic report tables generated from model outputs; LLM explains causal
   meaning, investigates contradictions and chooses additional sources.
5. Idempotent final-only DB writer, short rejected/active rows, website reader,
   weekly scheduler with run state, retries and missing-input statuses.
6. Actual token/time/source telemetry, keyed caching and changed-evidence
   reruns. Do not cache away contradictory evidence or required diverse sources.

## Per-report feedback loop

Record: which claim failed review; root cause (source, timing, units, inference,
calculation, narrative); generalizable rule; code/policy change; regression case;
remaining manual step; measured tokens and wall time when actually available.
Avoid generating the entire narrative after each new source. Freeze a reviewed
fact/assumption packet first, compute once, write one Korean evaluation report.
Only completed investment reports go to the report DB; evaluation PDFs remain
review artifacts. Operational status rows may still explain why research waits.
