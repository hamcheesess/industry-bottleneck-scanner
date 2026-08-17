# Industry Bottleneck Scanner

Upstream discovery engine for detecting emerging industry bottlenecks from cross-company operating signals.

The project starts from **phenomena**, not industry names. It scans company disclosures for recurring signals such as rising capex, accelerating demand, supply scarcity, and pricing power; aggregates those signals across companies; and surfaces clusters that deserve deeper industry research.

## Canonical discovery universe

The discovery universe is the **Russell 3000 membership universe**, represented as a dated immutable snapshot rather than a hard-coded list.

The registry preserves both issuer-level and security-level identity so source collection can remain reproducible across ticker changes, share classes, and SEC identity resolution.

```text
Russell 3000 membership snapshot
  -> normalized Universe Registry
  -> source adapters
  -> local candidate retrieval
  -> AtomicSignal
  -> cross-company industry aggregation
  -> signal acceleration
  -> research-trigger clusters
```

See [`docs/universe_contract.md`](docs/universe_contract.md).

## Responsibility boundary

This repository owns:

- Russell 3000 discovery-universe normalization and provenance
- transcript/disclosure source adapters and local caches
- phenomenon-based signal discovery
- Capex / Demand / Scarcity / Pricing normalization
- cross-company aggregation and acceleration
- semantic-only review queues and repeated novel-language discovery
- auditable Phase-1 experiment artifacts
- later: public-data validation, triangulation, value-chain mapping, bottleneck analysis, economic-capture analysis, and candidate discovery

This repository does **not** own full company underwriting, financial-risk adjudication, DCF valuation, or final investment reports. Those belong to the downstream `investment-research-automation` repository.

## Phase 1 pipeline

The current Phase-1 path is local-first and transcript-first:

```text
explicit ticker/fiscal-quarter requests
  -> transcript provider adapter
  -> cache-first bounded collection
  -> transcript quality diagnostics
  -> prepared/Q&A turn labeling
  -> keyword + regex retrieval
  -> optional local semantic retrieval
  -> deterministic adjudication
  -> AtomicSignal / semantic review queue
  -> matched current-vs-baseline issuer cohort
  -> industry-level aggregation
  -> signal acceleration
  -> trigger / confirmation hierarchy
  -> AtomicSignal JSONL + experiment JSON
```

Raw full transcripts are not sent to an LLM. The default development path uses no OpenAI API calls.

Frozen validation v1 is closed as source-coverage-limited under its Alpha-Vantage-only source contract. V2 is designed separately and now uses a **predeclared multi-source transcript architecture**: Alpha Vantage remains primary and Quartr edited transcripts are the preferred fallback. V2 fallback must preserve each issuer's current/baseline provider coherence and explicit provider provenance. The Quartr path remains draft-only until API access terms are accepted and credentials are available.

## Commands

Install the package in editable mode:

```bash
pip install -e .
```

Run the bounded real-data Phase-1 pilot after `ALPHA_VANTAGE_API_KEY` is available in the environment:

```bash
ibs-phase1-pilot
```

The pilot uses the matched request and dated metadata manifests under `experiments/`, caches successful transcripts under `var/transcripts/`, and writes runtime experiment artifacts under `var/`. Re-running it is cache-first, so successfully collected transcripts do not consume provider requests again.

Lower-level commands remain available for transcript collection, provider diagnostics, cache-only batch scans, and novel-language review:

```text
ibs-transcript-collect
ibs-pilot-diagnostics
ibs-phase1-batch
ibs-review-language
```

See [`docs/architecture.md`](docs/architecture.md), [`docs/transcript_source_strategy.md`](docs/transcript_source_strategy.md), [`docs/recall_strategy.md`](docs/recall_strategy.md), [`docs/signal_taxonomy.md`](docs/signal_taxonomy.md), [`docs/phase1_signal_contract.md`](docs/phase1_signal_contract.md), and [`docs/v2_validation_contract_draft.md`](docs/v2_validation_contract_draft.md).
