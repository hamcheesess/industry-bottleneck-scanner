# Discovery Handoff Contract

Repo A may emit a compact handoff preview for downstream underwriting, but it does not call or modify Repo B during Phase 1.

## Purpose

The handoff carries only discovery-state information needed to seed later company underwriting:

- schema version and generation time
- industry/cluster bucket and aggregation level
- discovery stage: `observing`, `watchlisted`, `triggered`, or `confirmed`
- deterministic discovery score used for ranking only
- current/baseline independent-company breadth
- metric-prevalence gains
- Demand + Scarcity core-pair state
- Capex/Pricing confirmation count
- issuer/ticker identities represented by current active evidence
- bounded evidence references with signal/document provenance

## Explicit exclusions

The handoff must not contain:

- DCF or intrinsic value
- target price
- company financial-risk decision
- investment recommendation or verdict
- final company report

Those remain responsibilities of the downstream underwriting repository.

## Gate

Phase 1 writes `handoff_preview.json` only for clusters that are already `triggered` or `confirmed`. Watchlisted and observing clusters remain inside Repo A for continued validation and do not enter the downstream queue.

The deterministic discovery score is not a replacement for trigger rules. It exists to rank clusters within the same stage while preserving explicit independent-company, core-pair, prevalence, and confirmation gates.
