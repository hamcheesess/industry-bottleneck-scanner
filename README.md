# Industry Bottleneck Scanner

Upstream discovery engine for detecting emerging industry bottlenecks from cross-company operating signals.

The project starts from **phenomena**, not industry names. It scans company disclosures for recurring signals such as rising capex, accelerating demand, supply scarcity, and pricing power; aggregates those signals across companies; and surfaces clusters that deserve deeper industry research.

## Canonical discovery universe

The discovery universe is the **Russell 3000 membership universe**, represented as a dated immutable snapshot rather than a hard-coded list.

The registry preserves both issuer-level and security-level identity so SEC filings can be collected by issuer/CIK while index membership and share classes remain reproducible.

```text
Russell 3000 membership snapshot
  -> normalized Universe Registry
  -> CIK / SEC identity resolution
  -> incremental SEC documents
  -> phenomenon scanner
```

See [`docs/universe_contract.md`](docs/universe_contract.md).

## Responsibility boundary

This repository owns:

- Russell 3000 discovery-universe normalization and provenance
- phenomenon-based signal discovery
- Capex / Demand / Scarcity / Pricing signal normalization
- cross-company aggregation
- signal acceleration and cluster detection
- later: public-data validation, triangulation, value-chain mapping, bottleneck analysis, economic-capture analysis, and candidate discovery

This repository does **not** own:

- full company underwriting
- company financial-risk adjudication
- DCF valuation
- final investment reports

Those belong to the downstream `investment-research-automation` repository.

## Phase 1

Phase 1 deliberately stops at:

```text
Russell 3000 universe snapshot
  -> normalized issuer/security registry
  -> source documents
  -> phenomenon vocabulary matching
  -> atomic signals
  -> company / industry aggregation
  -> signal acceleration
  -> research-trigger clusters
```

No live Russell-constituent download, live SEC ingestion, transcript vendor integration, or OpenAI API calls are enabled in the initial foundation.

See [`docs/architecture.md`](docs/architecture.md), [`docs/universe_contract.md`](docs/universe_contract.md), [`docs/signal_taxonomy.md`](docs/signal_taxonomy.md), and [`docs/phase1_signal_contract.md`](docs/phase1_signal_contract.md).
