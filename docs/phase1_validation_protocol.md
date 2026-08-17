# Phase 1 Expansion Validation Protocol

## Purpose

Phase 1 is a discovery-engine validation, not a demo that selected historical themes can be made to pass. The scanner must show four distinct properties:

1. source-backed phenomenon/extraction recall,
2. meaningful current-vs-baseline acceleration behavior,
3. precision on matched pre-event controls,
4. nontrivial blind discovery without outcome-aware cohort selection.

The repository keeps the original validation manifest as **frozen v1**. Observed failures may reveal correctness bugs, but they must not cause labels, vocabulary, or trigger thresholds to be edited until the validation round is complete.

## Current trusted local snapshot

The latest complete-cohort local snapshot contains six of seven frozen cases. The only unready case is `blind-proxy-2026`.

Current fresh-subset diagnostics are:

- fresh complete-cohort cases: `6/7`,
- positive stage recall: `66.7%`,
- expected-metric recall: `85.7%`,
- control false-positive rate: `33.3%` (`1/3`),
- freshness-filtered false-positive control: `auto-2019q2-control`.

The combined collection plan currently has `68/70` ticker-quarter requests cached. The two uncached requests are `MDGL:2026Q2` and `REZI:2026Q2`. The last bounded provider pass attempted both and received provider-missing responses rather than rate limits, local budget exhaustion, or ordinary provider errors. Those misses are a **source-layer coverage dependency**, not a scanner-calibration signal.

## Frozen v1 case contract

`experiments/phase1_validation_cases.csv` freezes case identity, role (`positive`, `control`, or `blind`), result path, aggregation level, positive expected bucket/metrics, external label-source URLs, and notes. Operational metadata paths may be supplied, but they do not change labels or evaluation rules.

Positive cases require at least one HTTP(S) label source. Aggregation-level mismatch blocks recovery rather than silently comparing unlike buckets.

## Validation readiness is stricter than result existence

A frozen validation case is scoreable only when all of the following are true:

1. current and baseline metadata both exist and parse successfully,
2. every metadata row has a real timezone-aware `published_at`,
3. every ticker-quarter in both frozen metadata windows is present in the normalized transcript cache,
4. a result exists under the current result schema,
5. its pipeline fingerprint matches current result-affecting code,
6. its input fingerprint matches the exact current metadata, cache, aggregation level, and company cap.

This prevents mixed-version scoring and prevents a frozen case from being scored after the comparable experiment silently shrinks to issuers with both cached windows.

## Partial metrics are diagnostics, not gate decisions

Until every frozen v1 case is freshness-approved, the validation state is `partial_waiting_data`. Fresh-subset strict recall, stage recall, metric recall, and control FPR are diagnostics only. `provisional_gate_ok` remains unset until the complete frozen manifest is available.

Repeatedly tuning the scanner against an incomplete denominator is prohibited.

## Routine cache-only validation cycle

```bash
ibs-phase1-validation-cycle
```

This reruns metadata-and-cache-ready frozen cases, checks complete-cohort provenance/freshness, evaluates frozen-v1 diagnostics, and regenerates calibration diagnostics from the exact same freshness-approved set. It does not call the provider or tune labels, vocabulary, or thresholds.

The cycle emits one next gate: `data_completion`, `frozen_v1_review`, or `blind_review_then_phase2_decision`.

## One-command provider resume

```bash
ibs-phase1-validation-resume
```

This performs one bounded cache-first Alpha Vantage collection pass, drafts metadata for newly complete request files, applies committed timestamp provenance where available, then runs one cache-only validation cycle. Rate limits stop the pass; they are never retried in a loop.

## Provider-missing transcript policy

A provider `missing` response is not treated as proof that the call did not occur, and it is not a scanner failure.

When every still-uncached request from a bounded pass has already returned provider-missing, with no rate limit, ordinary provider error, or local budget exhaustion, ordinary `ibs-phase1-validation-resume` calls reuse that terminal collection state and perform **zero repeated live requests**. The workflow reports:

```text
next_action=provider_missing_transcripts_review
```

Provider-missing is also not assumed to be permanent. A deliberate later bounded recheck is possible only through the explicit override:

```bash
ibs-phase1-validation-resume --retry-provider-missing
```

The override prevents accidental polling while preserving a controlled path for recent provider ingestion lag.

The frozen blind cohort must not be silently repaired by dropping, replacing, or shrinking issuers after results are available. A third-party transcript also must not be injected under the `alpha_vantage` identity. If the blind requests remain unavailable after source review, frozen v1 records a source-coverage limitation and the next validation contract must predeclare either a fallback-provider hierarchy or an outcome-blind reserve/replacement rule.

## Timestamp provenance

Fiscal-quarter labels are not event timestamps. Metadata drafting leaves `published_at` blank until a real timezone-aware event timestamp with HTTP(S) provenance is verified. Date-only transcript hints never become timestamps automatically.

Committed source-backed timestamp tables exist for the two 2021 positives and all three historical controls. The blind proxy is local validation-only output, so its exact event-time provenance is resolved only after its source coverage is complete.

## Positive diagnostics

Frozen v1 strict positive recovery requires aggregation match, expected bucket existence, at least watchlist stage, and every predeclared expected metric active in the current window. `positive_stage_recall` intentionally separates stage recovery from exact taxonomy recovery, but it does not replace the frozen v1 gate.

The frozen threshold is `0.67`; with three positives, `2/3 = 0.666...` does not pass. V1 is not rewritten after observing outcomes.

## Accepted correctness fixes

Two general extraction/provenance bugs were fixed without changing thresholds:

1. accepted retrieval candidates had lost vocabulary direction/negation/resolution semantics during promotion;
2. analyst questions could be promoted as issuer evidence in the production batch path.

The first completed semiconductor 2019 control no longer triggers after those fixes.

## Calibration freeze

Until frozen v1 is complete or explicitly closed with a documented source-coverage limitation, production extraction/aggregation behavior is frozen except for a general correctness invariant that can be reproduced without reference to whether a labeled case passes.

A missing expected metric or an observing known-positive case is not sufficient reason to change phrases, semantic thresholds, aggregation thresholds, or trigger contracts.

## Known v1 limitations

- The semiconductor 2021 external ground truth strongly supports supply-demand/capacity bottleneck conditions, while frozen v1 additionally requires exact `backlog_strength`; that taxonomy-specific miss is recorded but not tuned away.
- The power 2026 case compares Q2 against Q1 even though its external evidence already documents accelerating Q1 activity; an observing result can therefore be a temporal-label limitation rather than a trigger defect.
- The current blind source layer has two provider-missing Q2 requests (`MDGL`, `REZI`), which exposes source coverage as a first-class validation dimension.

## Frozen v1 metrics

- strict positive recovery recall >= 0.67,
- expected-metric recall >= 0.67,
- control false-positive rate <= 0.20,
- aggregation mismatches = 0.

These are development gates, not statistical-significance claims.

## Versioned v2 design

A future v2 contract must be created separately before outcomes are inspected and should separate:

1. phenomenon/extraction recall,
2. true window-to-window acceleration recall,
3. control precision,
4. blind discovery/ranking,
5. source coverage, including fallback-provider and missing-data rules.

V1 remains the audit trail and is never rewritten into v2 after the fact.

## Phase 2 gate

Proceed to public/physical validation and triangulation only after frozen v1 is either complete under one pipeline version or explicitly closed with a documented source-coverage limitation, unresolved correctness bugs are cleared, control behavior is reviewed, the blind result is reviewed when complete, and the v1 findings plus proposed v2 contract are reviewed as a whole.

Until then, Repo B remains untouched and no discovery result is treated as an investment candidate.
