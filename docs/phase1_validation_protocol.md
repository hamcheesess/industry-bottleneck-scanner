# Phase 1 Expansion Validation Protocol

## Purpose

Phase 1 is a discovery-engine validation, not a demo that selected historical themes can be made to pass. The scanner must show four distinct properties:

1. source-backed phenomenon/extraction recall,
2. meaningful current-vs-baseline acceleration behavior,
3. precision on matched pre-event controls,
4. nontrivial blind discovery without outcome-aware cohort selection.

The repository keeps the original validation manifest as **frozen v1**. Observed failures may reveal correctness bugs, but they must not cause labels, vocabulary, or trigger thresholds to be edited until the validation round is complete.

## Frozen v1 closure

Frozen v1 is formally closed as `closed_source_coverage_limited` under its Alpha-Vantage-only source contract. Six of seven frozen cases are fresh. The blind proxy is unscoreable because `MDGL:2026Q2` and `REZI:2026Q2` returned provider-missing and were not replaced, dropped, or backfilled from a different provider.

The fresh labeled/control subset remains diagnostic:

- fresh complete-cohort cases: `6/7`,
- positive stage recall: `66.7%`,
- expected-metric recall: `85.7%`,
- control false-positive rate: `33.3%` (`1/3`),
- freshness-filtered false-positive control: `auto-2019q2-control`.

Frozen v1 remains the audit trail. It is no longer a calibration target and does not become Phase-2-ready by later source backfilling.

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

## Provider-missing transcript policy retained for v1

A provider `missing` response is not treated as proof that the call did not occur, and it is not a scanner failure. Ordinary `ibs-phase1-validation-resume` calls reuse a terminal all-provider-missing collection state and perform zero repeated live requests. A deliberate diagnostic recheck remains available through `--retry-provider-missing`, but it does not reopen or rewrite frozen v1.

The frozen blind cohort must never be silently repaired by dropping, replacing, or shrinking issuers after results are available. A third-party transcript also must not be injected under the `alpha_vantage` identity.

## Accepted correctness fixes

Two general extraction/provenance bugs were fixed without changing thresholds:

1. accepted retrieval candidates had lost vocabulary direction/negation/resolution semantics during promotion;
2. analyst questions could be promoted as issuer evidence in the production batch path.

The first completed semiconductor 2019 control no longer triggers after those fixes.

## Known v1 limitations retained for audit

- The semiconductor 2021 external ground truth strongly supports supply-demand/capacity bottleneck conditions, while frozen v1 additionally requires exact `backlog_strength`; that taxonomy-specific miss is recorded but not tuned away.
- The power 2026 case compares Q2 against Q1 even though its external evidence already documents accelerating Q1 activity; an observing result can therefore be a temporal-label limitation rather than a trigger defect.
- The blind source layer exposed two provider-missing Q2 requests (`MDGL`, `REZI`), making source coverage a first-class validation dimension.
- The literal positive-recall gate is `0.67`; `2/3 = 0.666...` does not pass numerically.

## Frozen v1 metrics

- strict positive recovery recall >= 0.67,
- expected-metric recall >= 0.67,
- control false-positive rate <= 0.20,
- aggregation mismatches = 0.

These are retained development gates, not statistical-significance claims.

## V2 design status

The next gate is `v2_validation_contract_design`. V2 is a separately versioned contract and does not inherit or rewrite v1 outcomes.

The chosen source architecture is **predeclared multi-source transcript fallback**:

1. Alpha Vantage primary,
2. Quartr edited transcripts (`typeId=22`) as the preferred fallback.

Fallback is allowed only after an explicit primary-provider miss. Rate limits or provider errors stop the chain. Each issuer's current and baseline windows must resolve from the same provider; fallback therefore supplies the complete issuer pair rather than only the missing side. Provider mix across different issuers is allowed only with explicit provenance and reporting.

Quartr raw transcript type 15 is not eligible because the current scanner correctness contract depends on speaker/role provenance for analyst-question exclusion. Edited transcript speaker mapping is required.

This architecture is implemented only as a draft adapter/resolver layer. It is **not yet executable or frozen** because Quartr API access is a contact-sales product and no purchase/access decision has been made. Selecting the technical architecture does not authorize a subscription.

See `docs/v2_validation_contract_draft.md` and `experiments/v2_validation_policy.draft.json` for the full draft.

## V2 dimensions and draft gates

V2 separates:

1. source coverage,
2. phenomenon/extraction recall,
3. true window-to-window acceleration recall,
4. control precision,
5. blind discovery/ranking.

Draft integer gates avoid the v1 decimal-threshold ambiguity:

- extraction recall: at least `5/6`,
- acceleration watchlisted-or-stronger: at least `4/6`,
- acceleration triggered-or-stronger: at least `3/6`,
- controls: at most `1/8` triggered/confirmed false positives.

These are still draft values and cannot be used to claim a v2 pass before the contract is frozen.

## Phase 2 gate

Phase 2 remains blocked. Before Phase 2, the v2 source access decision, exact extraction cases, true acceleration windows, controls, blind ranking rubric, and evidence-review rules must be frozen before scanner outcomes are inspected. The full v2 run must then be reviewed without post-hoc threshold, cohort, source, or window changes.

Until then, Repo B remains untouched and no discovery result is treated as an investment candidate.
