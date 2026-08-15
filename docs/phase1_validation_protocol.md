# Phase 1 Expansion Validation Protocol

## Purpose

Phase 1 is not considered validated merely because transcript collection and signal extraction run successfully. The discovery engine must demonstrate that it can recover known operating bottlenecks, avoid firing on negative controls, and surface plausible clusters in a neutral sample without using the expected outcome during selection.

The validation sequence is deliberately ordered to separate recall, precision, and blind discovery behavior.

## Frozen case contract

Every validation case freezes before execution:

- `case_id`
- `role`: `positive`, `control`, or `blind`
- result path
- aggregation level: `sector`, `industry`, or `subindustry`
- expected bucket for positive cases
- expected metrics for positive cases
- external label-source URLs
- notes explaining the label/control rationale

Positive cases require at least one HTTP(S) label source. The evaluator also verifies that the result's aggregation level matches the frozen case. An aggregation mismatch blocks a positive recovery and blocks the overall validation pass rather than silently comparing unlike buckets.

The repository's initial frozen case set is `experiments/phase1_validation_cases.csv`.

## Stage A — known-positive recovery

Use historical periods where a bottleneck or demand/supply imbalance is independently documented outside the scanner.

Labels must be frozen before scanner output is inspected. A positive case is recovered only when:

1. the expected aggregation level matches the result,
2. the expected bucket reaches at least `watchlisted`, and
3. every predeclared expected metric is present in the current-window active metrics.

The purpose is to test whether the vocabulary/retrieval stack can recover a real phenomenon, not whether thresholds can be tuned until a selected example fires.

The initial positive set contains:

- the 2021 semiconductor shortage at sector level,
- the 2021 downstream auto chip shortage at sector level,
- the existing 2026 electrical-equipment pilot at industry level.

The existing power pilot remains in the validation set even though the current scanner missed the production trigger. Its negative result is not rewritten after the fact.

## Stage B — negative controls

Controls should match source type, company cohort, and temporal structure as closely as practical while preceding the labeled shock.

The initial controls therefore use pre-shortage 2019 windows for the same semiconductor and auto cohorts rather than unrelated contemporary sectors. This makes the precision test materially harder and reduces the chance that a generic sector difference is mistaken for scanner precision.

A control is counted as a false positive if any cluster reaches `triggered` or `confirmed`. `observing` and `watchlisted` states remain diagnostic and are not counted as production false positives.

## Stage C — blind validation-only proxy cohort

Blind cases have no expected bucket and do not contribute to label-based pass/fail metrics. Selection must happen before transcript signals are inspected and may use identity/classification metadata only.

For Phase-1 validation only, the approved free broad-U.S. proxy is the public iShares Russell 3000 ETF (`IWV`) holdings CSV. It is explicitly **not** canonical Russell 3000 membership.

The public holdings file exposes sector but not granular industry. Therefore:

- the proxy plan records `canonical_russell_3000=false`;
- it records `purpose=phase1_validation_only`;
- placeholder `proxy-sector::<sector>` labels are used only to satisfy the generic sampler contract;
- the resulting experiment must run with `aggregation_level=sector`;
- passing the proxy validation does not authorize proxy holdings for production discovery.

`ibs-phase1-proxy-plan` downloads the dated holdings file, makes a stable scanner-blind selection, and emits paired transcript requests.

The blind sampler is trigger-reachable by construction. The production trigger needs at least three independent companies in one aggregation bucket, so the default blind plan selects three groups with four companies each: 12 issuers and 24 ticker-quarter requests. The fourth company supplies one unit of coverage slack.

## Transcript collection

Frozen labeled request manifests live under `experiments/validation_*_requests.csv`. The blind request file is generated under `var/cohort/neutral_proxy_requests.csv`.

`ibs-phase1-validation-collect` deduplicates all available labeled and blind requests and applies one global Alpha Vantage provider budget. It is cache-first and safe to re-run on later days. The default budget is 24 provider calls so a free-tier daily ceiling is not intentionally exhausted by the command itself.

Collection status is written to `var/validation/collection-status.json`. Already-cached ticker-quarter pairs consume no provider budget.

## Event-date metadata drafting

Cached transcripts still do not authorize inventing publication timestamps. Fiscal-quarter labels are period identifiers, not event dates.

`ibs-phase1-validation-metadata-draft` creates separate current and baseline metadata CSV drafts plus a research checklist. It always leaves `published_at` blank until a real timezone-aware timestamp is independently verified.

For convenience, the command scans the first transcript turns for unambiguous written calendar dates such as `August 13, 2026`. Those values are emitted only as `published_date_candidate` and `published_date_evidence`; they are not promoted into `published_at`, no time of day is invented, and numeric-only dates are ignored. If multiple distinct written dates appear, no candidate date is selected.

The generic metadata loader ignores these extra research columns, so completed drafts remain compatible with `ibs-phase1-batch` after `published_at` and provenance are filled.

## Verified timestamp provenance

For the three request files already complete in the local cache, event timestamps were independently verified from issuer investor-relations pages, issuer-hosted SEC filing mirrors, or issuer-hosted historical earnings releases. The frozen provenance files are:

- `experiments/verified_timestamps_semiconductor_2021.csv`
- `experiments/verified_timestamps_auto_2021.csv`
- `experiments/verified_timestamps_semiconductor_2019q2_control.csv`

Every row contains ticker, fiscal-quarter label, an ISO-8601 timestamp with explicit UTC offset, and the HTTP(S) source URL supporting the conference-call date and local time. Daylight-saving offsets are preserved explicitly rather than inferred later.

`ibs-phase1-validation-metadata-finalize` remains fail-closed: verified rows must match the draft ticker+quarter set exactly, timestamps must be timezone-aware, and every row must carry HTTP(S) provenance.

`ibs-phase1-validation-advance` is the convenience path for these frozen provenance files. It applies only the committed verified rows that exactly match an existing local draft, finalizes current and baseline metadata in place, then invokes `ibs-phase1-validation-run`. Cases whose transcript cache or draft metadata are still incomplete remain skipped; no missing timestamp is guessed.

## Validation metrics

`ibs-phase1-validate` evaluates a CSV manifest pointing to completed `ibs-phase1-batch` result JSON files.

Primary metrics:

- positive recovery recall
- expected-metric recall
- control false-positive rate
- aggregation-level mismatch count

Default viability thresholds are intentionally explicit rather than hidden in a composite score:

- positive recovery recall >= 67%
- expected-metric recall >= 67%
- control false-positive rate <= 20%
- aggregation mismatches = 0

These are development gates, not claims of statistical significance. They should be revisited only after sample size expands; they must not be changed merely to make a failing cohort pass.

## Manifest format

```csv
case_id,role,result_path,aggregation_level,expected_bucket,expected_metrics,label_sources,notes
power-positive,positive,var/validation/power-positive.json,industry,Electrical Equipment,backlog_strength|capacity_constraint,https://example.com/source,labels frozen before run
matched-control,control,var/validation/control.json,sector,,,https://example.com/context,matched pre-event control
blind-01,blind,var/validation/blind-01.json,sector,,,,scanner-blind proxy sample
```

## Execution

```text
freeze source-backed labels / pre-event controls
  -> generate scanner-blind proxy cohort
  -> collect bounded paired transcripts cache-first
  -> create metadata drafts without fabricating timestamps
  -> verify real event timestamps and provenance
  -> finalize exact-match metadata
  -> run cache-only matched current/baseline experiments
  -> freeze result JSON
  -> evaluate manifest with ibs-phase1-validate
  -> inspect blind results only after freezing
  -> decide whether Phase 1 is viable for Phase 2
```

Fiscal-quarter labels must never be converted into fake publication timestamps. Exact or explicitly sourced event metadata remains a separate provenance step before batch scanning.

The validation evaluator never changes scanner vocabulary, trigger thresholds, discovery scores, or result files.

## Phase 2 gate

Proceed to public/physical validation and triangulation only after:

1. the labeled validation manifest passes the declared recall/false-positive gates,
2. all frozen aggregation levels match their experiment outputs,
3. at least one blind cohort produces a plausible nontrivial ranking without theme preselection,
4. evidence concentration and missing-data diagnostics do not explain the result,
5. the discovery result is reproducible from cached data.

Until then, Repo B remains untouched and no discovery result is treated as an investment candidate.
