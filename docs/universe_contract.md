# Universe Contract

## Canonical discovery universe

The canonical discovery universe is a dated snapshot of active U.S.-listed common stocks.
It is provider-independent after normalization and is not licensed-index membership.

Canonical identifier:

```text
broad_us_common_stocks_v1
```

The initial production adapter uses Massive reference data with these explicit filters:

- `market=stocks`, `locale=us`, `active=true`, `type=CS`;
- primary listing on NYSE, Nasdaq, NYSE American, NYSE Arca, or Cboe BZX MICs;
- OTC securities, ETFs, funds, warrants, preferred stock, and other non-common-stock types
  are excluded.

This intentionally differs from Russell 3000 membership. A licensed Russell snapshot may
be added later as a comparison tag or validation benchmark, but it does not redefine the
canonical production universe.

## Why the universe registry is separate from scanning

The phenomenon scanner does not know how membership was sourced. It consumes a normalized
registry with stable issuer/security identifiers. Provider replacement remains an adapter
change rather than a scanner or causal-pipeline rewrite.

## Issuer vs security

The registry distinguishes:

- `issuer_id`: the underlying SEC reporting issuer when resolvable;
- `security_id`: the specific listed security/share class.

Massive CIK and OpenFIGI fields are preserved. Multiple securities may map to one issuer
because SEC filings are issuer-level while market observations are security-level.

## Required normalized fields

```json
{
  "security_id": "stable security identifier",
  "issuer_id": "stable issuer identifier",
  "ticker": "normalized ticker",
  "company_name": "issuer/security display name",
  "exchange": "primary listing MIC",
  "cik": "optional 10-digit SEC CIK",
  "memberships": ["broad_us_common_stocks_v1", "optional additional tags"],
  "active": true
}
```

The market snapshot extends this with:

```text
sector,bucket,classification_system,classification_code
```

The initial classification is explicitly `SEC_SIC`: `sector` is the SIC division and
`bucket` is the SIC code plus provider description. It must not be labelled GICS. Missing
SIC remains an explicit unclassified coverage gap.

## Free-plan checkpoint contract

`ibs-massive-universe` performs two cache-first operations:

1. paginated dated `All Tickers` retrieval;
2. per-ticker overview enrichment for SIC and stable identifiers.

The Massive Basic execution defaults to 13 seconds between uncached requests. Raw validated
responses are cached before normalized artifacts are rebuilt. `--max-overview-requests`
bounds one job; later jobs restore the cache and resume without re-requesting completed
tickers.

A per-ticker overview HTTP 400 or 404 is checkpointed as a terminal enrichment gap rather
than aborting the broad-US run. The member remains in the canonical denominator and appears in
`overview_error_tickers`; only its optional overview/SIC enrichment is absent. Authentication,
entitlement, rate-limit, transport, pagination, and response-contract failures still stop the
run instead of being silently downgraded.

The GitHub bootstrap workflow runs seven sequential jobs of at most 800 uncached overview
requests each. Each job stays below the hosted-runner timeout; the final job starts the
market backfill only when no overview requests remain.

Manual historical calibration runs accept separate `universe_as_of` and `market_as_of` inputs.
This permits a genuine dated membership/classification snapshot to remain frozen while the
normalized price archive extends to a later cutoff. `market_as_of < universe_as_of` is rejected
before provider collection starts.

Every run writes:

- `market_universe.csv`, including pending/unclassified members rather than shrinking the
  denominator;
- `manifest.json` with source, date, filter/classification semantics, counts, checkpoint
  status, and SHA-256 of the normalized CSV.

An incomplete run has `enrichment_status=enrichment_in_progress`. Completion with genuine
provider SIC gaps is distinct: `complete_with_classification_gaps`.
The manifest separately records `overview_error_count` and `overview_error_tickers` so provider
reference anomalies cannot be confused with ordinary missing SIC fields.

## Snapshot provenance and replay

Every normalized snapshot records `universe_id`, `as_of`, source, member count,
classification coverage, and normalized fingerprint. Production snapshots are immutable.
A replay date earlier than its universe snapshot remains invalid; future multi-date replay
must use a universe snapshot that existed at or before each replay cutoff.

## Historical validation proxy

The public IWV holdings parser remains a legacy Phase-1 validation proxy. It is not the
canonical production membership source and may not be relabelled as
`broad_us_common_stocks_v1`.
