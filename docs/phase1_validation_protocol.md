# Phase 1 Expansion Validation Protocol

## Purpose

Phase 1 is a discovery-engine validation, not a demo that selected historical themes can be made to pass. The scanner must show four distinct properties:

1. source-backed phenomenon/extraction recall,
2. meaningful current-vs-baseline acceleration behavior,
3. precision on matched pre-event controls,
4. nontrivial blind discovery without outcome-aware cohort selection.

The repository keeps the original validation manifest as **frozen v1**. Observed failures may reveal correctness bugs, but they must not cause labels, vocabulary, or trigger thresholds to be edited until the validation round is complete.

## Frozen v1 case contract

`experiments/phase1_validation_cases.csv` freezes:

- `case_id`
- `role`: `positive`, `control`, or `blind`
- result path
- aggregation level
- expected bucket for positive cases
- expected metrics for positive cases
- external label-source URLs
- notes

The manifest may also contain `current_metadata_path` and `baseline_metadata_path`. Those fields are **operational inputs only**. They make a frozen case reproducible and do not change its label or evaluation rule. Cases without explicit paths use `var/validation/metadata/<case>-current.csv` and `...-baseline.csv`.

Positive cases require at least one HTTP(S) label source. Aggregation-level mismatch blocks recovery rather than silently comparing unlike buckets.

## Result freshness is part of correctness

A result file is not valid merely because it exists.

Every `ibs-phase1-batch` result now carries `result_provenance` containing:

- a versioned result schema,
- a deterministic fingerprint of result-affecting scanner/pipeline code,
- a deterministic fingerprint of current/baseline metadata plus normalized transcript-cache inputs,
- the provider and metadata paths used by the run.

`ibs-phase1-validation-ready` evaluates only results whose schema, pipeline fingerprint, and input fingerprint match the current environment. Old files with no provenance, results generated before a scanner fix, and results whose local inputs changed are reported as stale and do not enter interim validation metrics.

This prevents a mixed-version validation set, such as combining newly recalibrated semiconductor cases with an older power-pilot result.

## Routine cache-only validation cycle

The normal local validation command is now:

```bash
ibs-phase1-validation-cycle
```

It performs one bounded bundle:

```text
all metadata-ready frozen cases
  -> cache-only batch rerun
  -> result provenance / freshness check
  -> interim frozen-v1 evaluation
  -> calibration diagnostics
  -> one consolidated cycle-status JSON
```

It does **not** call the transcript provider, change labels, tune vocabulary, or change trigger thresholds. Narrow commands such as evidence audit remain available for exceptional debugging, not as the default run-after-run workflow.

Provider collection remains a separate activity and should only be resumed when quota is available.

## Positive diagnostics: stage recall versus strict v1 recovery

Frozen v1 strict recovery is preserved exactly for audit. A positive case is `positive_recovered` only when:

1. aggregation level matches,
2. expected bucket exists,
3. expected bucket reaches at least `watchlisted`,
4. every predeclared expected metric is active in the current window.

Because this couples cluster recovery to exact taxonomy recovery, the evaluator now also reports `positive_stage_recovered` and `positive_stage_recall`. Stage recovery uses rules 1–3 and intentionally ignores exact metric misses.

These are **diagnostics, not a silent gate change**. The v1 pass/fail CLI continues to use the original strict positive-recall gate plus expected-metric recall, control FPR, and aggregation consistency.

This separation is important because a confirmed cluster with one taxonomy miss is a different failure mode from a cluster that never reaches watchlist, and neither should automatically trigger vocabulary tuning.

## Frozen v1 threshold arithmetic

The current CLI default is `--min-positive-recall 0.67`.

With exactly three positive cases, two recovered cases produce `2 / 3 = 0.666...`, which is below the literal numeric threshold `0.67`. Therefore the current v1 strict gate requires 3/3 positives at this sample size. The code does not round 2/3 upward for pass/fail.

This is recorded as a v1 contract property. It must not be silently changed after seeing results. Any future use of an exact two-of-three rule belongs in a versioned v2 validation contract.

## Calibration findings already accepted as correctness fixes

Two general provenance/extraction bugs were found with matched controls and fixed without changing thresholds:

1. accepted retrieval candidates had lost vocabulary direction/negation/resolution semantics during promotion;
2. analyst questions could be promoted as issuer evidence in the production batch path.

The first fix reconstructs evidence semantics before AtomicSignal promotion. The second keeps analyst turns for transcript/Q&A provenance but excludes them from lexical/semantic candidate production; management answers remain eligible.

After those fixes, the first completed semiconductor 2019 control no longer reaches the production trigger. Its remaining management-origin `backlog_strength` evidence is preserved rather than removed to make the control cleaner.

## Calibration freeze from this point

Until the remaining frozen controls and blind cohort are collected and evaluated, production extraction/aggregation behavior is frozen except for a **general correctness invariant**.

A further change is allowed only when all of the following are true:

1. it is a source/provenance/data-contract error rather than a desired validation outcome,
2. the error can be expressed without referring to whether a particular labeled case passes,
3. a generic or synthetic regression test reproduces it,
4. the fix does not alter a frozen label or loosen/tighten a gate merely to improve current metrics.

A missing expected metric in a known positive is not, by itself, sufficient reason to add phrases or alter semantic thresholds. Likewise, an `observing` known-domain case is not sufficient reason to relax acceleration gates.

## Known v1 label limitations discovered during review

The v1 manifest remains unchanged, but two limitations are now explicit so they are not accidentally optimized against.

### Semiconductor shortage 2021

The frozen Commerce sources strongly support a semiconductor supply-demand mismatch and wafer/fabrication-capacity bottleneck. The v1 manifest additionally requires the exact scanner metric `backlog_strength`. That exact metric is more taxonomy-specific than the external label source.

Therefore a `backlog_strength` miss is recorded as a v1 strict-metric miss, but it is **not** evidence that the scanner vocabulary should be expanded until a source-grounded extraction review independently supports that change.

### Power infrastructure 2026

The frozen power pilot compares Q2 against Q1. One of its external sources is an Eaton Q1 release whose title itself describes accelerating Q1 sales, orders, and backlog. It is useful evidence that the domain was active, but it is not an independent proof that Q2 accelerated relative to Q1.

Therefore an `observing` Q2-vs-Q1 power result may reflect a temporal-label limitation rather than a trigger defect. Frozen v1 keeps the case unchanged for audit; it must not be used to justify threshold relaxation.

## Stage A — source-backed positives

The frozen v1 positives remain:

- semiconductor shortage 2021, sector level,
- downstream auto chip shortage 2021, sector level,
- power/electrical infrastructure 2026, industry level.

The evaluator reports both strict v1 recovery and stage recovery, plus expected-metric hits/misses.

## Stage B — matched negative controls

Controls use the same source type and, where practical, the same issuer cohort before the labeled shock. A control is a false positive only if a cluster reaches `triggered` or `confirmed`; `observing` and `watchlisted` remain diagnostic states.

Current frozen controls are:

- semiconductor 2019 Q2/Q1,
- semiconductor 2019 Q3/Q2,
- auto 2019 Q2/Q1.

Control evidence can be decomposed with the evidence-audit commands when a genuine trigger remains after the full routine cycle.

## Stage C — blind validation-only proxy

The blind cohort uses the approved public IWV holdings proxy only for Phase-1 validation. It remains explicitly noncanonical for production Russell 3000 membership.

The proxy plan:

- is selected before scanner outcomes are inspected,
- uses sector aggregation because the public holdings file does not provide the required granular industry field,
- selects enough independent companies per group to make the production trigger reachable,
- cannot contribute a label-based positive or control pass/fail score.

A blind result is inspected only after its result is frozen and fresh under the same pipeline used for labeled cases.

## Transcript collection and timestamp provenance

`ibs-phase1-validation-collect` is cache-first and bounded. Already cached ticker-quarter pairs consume no provider budget. Collection status records per-request-file coverage and missing pairs.

Fiscal-quarter labels are not event timestamps. Metadata drafting always leaves `published_at` blank until a real timezone-aware event timestamp with HTTP(S) provenance is verified. Date-only transcript hints never become timestamps automatically.

`ibs-phase1-validation-metadata-finalize` remains fail-closed on exact ticker+quarter coverage, timezone-aware timestamps, and provenance URLs.

## Frozen v1 validation metrics

The original development gates remain:

- strict positive recovery recall >= 0.67,
- expected-metric recall >= 0.67,
- control false-positive rate <= 0.20,
- aggregation mismatches = 0.

`positive_stage_recall` is reported alongside those metrics but does not replace the frozen v1 strict gate.

These are development gates, not statistical-significance claims.

## Versioned v2 design after v1 collection completes

The current review shows that v1 combines several different questions inside one positive definition. A future **v2 manifest must be created separately**, before its outcomes are inspected, and should separate:

1. **phenomenon/extraction recall** — does the current window recover source-backed signal families without requiring acceleration?
2. **acceleration recall** — only cases with independent evidence that the exact current window strengthened versus the exact baseline window;
3. **control precision** — matched pre-event controls under the same pipeline;
4. **blind discovery/ranking** — outcome-blind cohort selection and post-freeze plausibility review.

V1 is never rewritten into v2 after the fact. V1 remains an audit trail of the initial validation design and its limitations.

## Phase 2 gate

Proceed to public/physical validation and triangulation only after:

1. all frozen v1 result files are fresh under one pipeline version,
2. the complete frozen manifest has been evaluated without unresolved correctness bugs,
3. control behavior is within the declared precision gate,
4. the blind result is plausible and not explained by missing data or issuer concentration,
5. results are reproducible from cached inputs,
6. the v1 findings and the proposed v2 contract are reviewed as a whole rather than tuned one case at a time.

Until then, Repo B remains untouched and no discovery result is treated as an investment candidate.
