# Market trigger execution contract

This document specifies the executable Phase-1 boundary. The architectural intent and
development order remain canonical in [`current_roadmap.md`](current_roadmap.md).

## Dated market universe input

The canonical production ID is `broad_us_common_stocks_v1`. The initial adapter generates
it from a dated Massive active-U.S.-common-stock reference snapshot and SEC SIC enrichment.
Provider response schemas stop at `massive_universe.py`; the CSV remains the stable market
input contract.

`ibs-market-trigger` accepts a CSV extending the existing broad-US universe identity
contract. Required columns are:

```text
ticker,company_name,sector,bucket
```

Existing optional identity columns remain supported, including `security_id`, `issuer_id`,
`exchange`, `cik`, `memberships`, and `active`.

The CLI separately requires the membership snapshot's `--universe-as-of` and
`--universe-source`. A universe snapshot later than the market `--as-of` is rejected.
Rows with blank sector or bucket remain in the active-member denominator and are emitted as
`unclassified_tickers`; they are not silently discarded.

ETF membership does not define a bucket. Each bucket is aggregated from its listed-company
members. The benchmark ticker is used only for broad-market relative returns.

## Provider boundary

`MassiveGroupedDailyClient` calls the adjusted all-US-stocks grouped-daily endpoint once per
requested weekday. Provider fields are normalized immediately into `DailyBar`; downstream
market feature and trigger modules do not import or call the provider.

Raw responses are cached by date only after response validation. Authentication, quota, and
provider errors therefore remain retryable. Weekend calls are skipped. Missing symbols and
symbols with fewer than the minimum required observations are explicit coverage fields.

The initial backfill is quota-sensitive. The CLI defaults to a 13-second interval between
uncached requests; incremental runs reuse cache entries.

The free-plan MVP freezes the first production snapshot and market cutoff at `2026-08-21`
and backfills price/volume from `2024-11-01`. This does not authorize replay before the
universe snapshot date; historical calibration requires separately dated membership
snapshots at or before each replay cutoff.

## Normalized history archive

`market_history.jsonl` is a self-contained `normalized-market-history-v1` archive containing:

- archive `as_of` and source;
- benchmark identity and bars;
- constituent adjusted close/volume bars with sector and bucket;
- universe identity/classification provenance;
- missing, insufficient-history, provider, and cache coverage diagnostics.

The first record is a manifest; remaining records are normalized benchmark or constituent
bars. This archive is the replay input and contains no provider-specific response schema.

For historical calibration, universe and market cutoffs are deliberately separate. A dated
historical membership/classification snapshot may be held fixed while normalized price history
continues through a later market cutoff. Replay dates must be on or after `universe.as_of` and on
or before the archive `as_of`; the system never substitutes a future membership snapshot.

## Trigger artifact

`industry_market_triggers.json` uses schema `industry-market-trigger-v1` and contains:

- explicit `as_of`, generation timestamp, source, and benchmark;
- `company_membership_bottom_up` aggregation marker;
- complete trigger policy thresholds;
- universe and collection coverage;
- ranked bucket results including breadth, medians, score, gate reasons, and `triggered`.

## Strict-as-of replay

`ibs-market-trigger-replay` accepts a normalized archive and an earlier or equal replay date.
It rejects:

- replay dates after the archive cutoff;
- universe snapshots dated after the replay cutoff;
- unsupported archive schemas or inconsistent benchmark records.

All feature calculation reuses `market_history.build_market_snapshots`, whose normalization
excludes bars after the replay `as_of`. Replay does not call Massive and does not extend any
legacy `validation_*` state machine.

## Dated calibration series

`ibs-market-trigger-calibrate` consumes only a persisted normalized archive and makes zero
provider calls. It emits `industry_market_triggers.json` below an `as_of=YYYY-MM-DD` directory
for the first eligible session, each last available benchmark session of the month, and the
requested final session. `calibration_manifest.json` records:

- the normalized-history SHA-256 and frozen universe/archive provenance;
- the unchanged trigger policy with `frozen_observation_only_no_threshold_tuning` status;
- per-date benchmark-session, eligible-ticker, insufficient-history, bucket, and trigger counts;
- each dated artifact path and SHA-256;
- `provider_calls: 0`.

The command rejects a calibration start before `universe.as_of`, an end after archive `as_of`,
and any benchmark or constituent bar after the archive cutoff. Eligibility is recomputed at
every date using the 127-session minimum; later history is never used to make an earlier ticker
eligible.

## Outcome-blind quality review and research queue

`ibs-market-trigger-quality` verifies every dated artifact hash, policy, universe provenance,
date ordering, and bucket identity before calculating trigger prevalence, adjacent-date Jaccard,
and bucket persistence. It does not consume outcomes, news, filings, or later prices and cannot
change the frozen trigger policy. A latest trigger is classified as `persistent` only when it is
present on at least two consecutive calibration dates; otherwise it remains `emerging`.

`ibs-market-trigger-research-queue` joins every latest persistent bucket back to the dated
universe CSV and emits SEC-compatible issuer batches of at most 100 rows. All issuers in the
selected buckets are retained; the batching rule does not handpick companies. Multiple share
classes sharing one CIK are collected once at the SEC issuer boundary, with skipped security
tickers recorded in the queue manifest. Missing CIKs are also explicit and never counted as
selected issuers.
