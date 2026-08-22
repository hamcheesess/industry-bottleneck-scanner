# Market trigger execution contract

This document specifies the executable Phase-1 boundary. The architectural intent and
development order remain canonical in [`current_roadmap.md`](current_roadmap.md).

## Dated market universe input

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

## Normalized history archive

`market_history.jsonl` is a self-contained `normalized-market-history-v1` archive containing:

- archive `as_of` and source;
- benchmark identity and bars;
- constituent adjusted close/volume bars with sector and bucket;
- universe identity/classification provenance;
- missing, insufficient-history, provider, and cache coverage diagnostics.

The first record is a manifest; remaining records are normalized benchmark or constituent
bars. This archive is the replay input and contains no provider-specific response schema.

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
