# Industry Bottleneck Scanner

Upstream discovery engine for detecting economically important industry bottlenecks and second-/third-order beneficiaries from market-triggered causal research.

The current target architecture starts from **observable market anomalies**, asks whether the move is supported by a structural operating demand shock, and then expands through the value chain to find nodes where a new demand branch meets pre-existing supply constraints, independent demand roots, economic capture, reinvestment runway, and a still-open expectations gap.

The system does **not** try to predict every quiet industry before the market reacts, and it does not treat a lagging stock as automatically cheap.

## Canonical discovery universe

The discovery universe is the **Russell 3000 membership universe**, represented as a dated immutable snapshot rather than a hard-coded list.

The registry preserves issuer- and security-level identity so market data, disclosures, transcript sources, and later company mapping remain reproducible across ticker changes, share classes, and SEC identity resolution.

```text
Russell 3000 membership snapshot
  -> normalized Universe Registry
  -> Market Trigger
  -> Causal Diagnosis
  -> Root Demand Shock
  -> Value-chain Hypothesis Graph
  -> Evidence-backed Edge Approval
  -> Pre-shock Industry State Lookup
  -> Demand Convergence
  -> Pre-News Chain Selection
  -> Bottleneck / Economic Capture Ranking
  -> Listed-company Mapping
  -> Repo B Underwriting
```

A parallel low-frequency state loop maintains append-only supply-side snapshots for economically meaningful nodes. The event-driven market loop queries only state that existed **strictly before** a later market trigger, which makes historical replay look-ahead safe.

See [`docs/universe_contract.md`](docs/universe_contract.md) and [`docs/market_triggered_causal_discovery.md`](docs/market_triggered_causal_discovery.md).

## Responsibility boundary

This repository owns:

- Russell 3000 discovery-universe normalization and provenance
- market-trigger detection and industry/subindustry breadth
- transcript/disclosure source adapters and local caches
- Capex / Demand / Scarcity / Pricing operating-signal normalization
- cross-company aggregation and acceleration
- persistent industry-state history for supply constraints
- causal value-chain hypothesis representation
- evidence-backed edge approval and triangulation
- multi-root demand convergence at shared constrained nodes
- pre-news bottleneck / economic-capture research ranking
- listed-company exposure mapping
- small auditable handoff manifests for downstream underwriting

This repository does **not** own full company underwriting, financial-risk adjudication, DCF valuation, or final investment reports. Those belong to the downstream `investment-research-automation` repository.

## Existing operating scanner

The current implemented scanner remains local-first and mostly transcript-first:

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

Frozen validation v1 is closed as source-coverage-limited under its Alpha-Vantage-only source contract. That experiment remains an audit trail; it is not the architecture for the next discovery stage.

Transcript completeness is no longer intended to gate discovery. Transcripts become one operating-evidence source alongside earnings releases, SEC disclosures, investor presentations, customer/supplier evidence, and physical industry data.

## Market-triggered causal discovery

The next architecture is deliberately slower than real-time trading and does not require headline-speed data. End-of-day or weekly market anomalies are sufficient to start research.

The provider-independent causal core is defined in `causal_expansion.py`. It ranks value-chain nodes on six transparent dimensions:

- demand transmission,
- bottleneck strength,
- economic capture,
- reinvestment runway,
- triangulation,
- expectation gap.

The persistent supply-side memory is defined in `industry_state.py`. Each historical snapshot scores supply inelasticity, lead-time pressure, capacity tightness, capacity-expansion difficulty, qualification barriers, and pricing pressure. The append-only registry preserves what was known before later market triggers.

The convergence core is defined in `demand_convergence.py`. It distinguishes multiple paths from the same root shock from genuinely independent demand roots, and promotes shared downstream nodes only when the new trigger reaches a node that was already constrained before the trigger.

Hard gates prevent a high weighted score from hiding a weak causal link. Historical validation must freeze an `as_of` date so later large contracts or earnings surprises cannot leak backward into the original candidate decision.

The governing draft policy is [`experiments/market_triggered_discovery_policy.draft.json`](experiments/market_triggered_discovery_policy.draft.json).

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

See [`docs/architecture.md`](docs/architecture.md), [`docs/market_triggered_causal_discovery.md`](docs/market_triggered_causal_discovery.md), [`docs/transcript_source_strategy.md`](docs/transcript_source_strategy.md), [`docs/recall_strategy.md`](docs/recall_strategy.md), [`docs/signal_taxonomy.md`](docs/signal_taxonomy.md), and [`docs/phase1_signal_contract.md`](docs/phase1_signal_contract.md).
