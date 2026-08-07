# Universe Contract

## Canonical discovery universe

The canonical discovery universe is the **Russell 3000 membership universe**.

The scanner treats the universe as a dated membership snapshot, not as a hard-coded list of exactly 3,000 rows. Membership can change through reconstitution, corporate actions, delistings, mergers, and share-class changes.

Canonical identifier:

```text
russell_3000
```

## Why the universe registry is separate from scanning

The phenomenon scanner should not care how index membership was sourced. It consumes a normalized registry with stable issuer/security identifiers.

This separation allows future adapters for licensed index files, manually supplied snapshots, or other authoritative constituent feeds without changing scanner logic.

## Issuer vs security

The registry distinguishes:

- `issuer_id`: the underlying SEC reporting issuer when resolvable
- `security_id`: the specific listed security/share class

Multiple securities may map to one issuer. This is important because SEC filings are issuer-level while index membership and tickers are security-level.

## Required normalized fields

```json
{
  "security_id": "stable security identifier",
  "issuer_id": "stable issuer identifier",
  "ticker": "normalized ticker",
  "company_name": "issuer/security display name",
  "exchange": "optional exchange",
  "cik": "optional 10-digit SEC CIK",
  "memberships": ["russell_3000", "optional additional tags"],
  "active": true
}
```

The minimum raw CSV input columns are:

```text
ticker,company_name
```

Recommended columns are:

```text
security_id,issuer_id,ticker,company_name,exchange,cik,memberships,active
```

## SEC resolvability

SEC ingestion requires a CIK. Universe members therefore fall into two groups:

- `sec_resolvable_members`: active members with a normalized CIK
- `unresolved_members`: active members without a CIK

Unresolved members should be enriched through a separate identifier-resolution step before SEC document ingestion. They must not silently disappear from the universe.

## Membership tags

`russell_3000` is always included. Other index memberships such as `sp500`, `nasdaq100`, or `russell2000` can be preserved as metadata but must not create duplicate universe members.

## Snapshot provenance

Every `UniverseSnapshot` records:

- `universe_id`
- `as_of`
- `source`
- normalized members

Production snapshots should be immutable artifacts so later signal results can be reproduced against the exact universe used for that run.

## Explicit non-goals for this phase

This contract does not yet:

- download Russell index constituents
- choose or license a constituent data vendor
- resolve missing CIKs
- fetch SEC filings
- remove companies based on financial quality

Financial quality belongs downstream. The discovery universe should remain broad so emerging bottleneck beneficiaries are not filtered out before the phenomenon scan.
