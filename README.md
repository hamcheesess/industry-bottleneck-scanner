# Industry Bottleneck Scanner

Upstream discovery engine for detecting emerging industry bottlenecks from cross-company operating signals.

The project starts from **phenomena**, not industry names. It scans company disclosures for recurring signals such as rising capex, accelerating demand, supply scarcity, and pricing power; aggregates those signals across companies; and surfaces clusters that deserve deeper industry research.

## Responsibility boundary

This repository owns:

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
source documents
  -> phenomenon vocabulary matching
  -> atomic signals
  -> company / industry aggregation
  -> signal acceleration
  -> research-trigger clusters
```

No live SEC ingestion, transcript vendor integration, or OpenAI API calls are enabled in the initial foundation.

See [`docs/architecture.md`](docs/architecture.md) and [`docs/phase1_signal_contract.md`](docs/phase1_signal_contract.md).
