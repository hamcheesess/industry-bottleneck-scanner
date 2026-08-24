# Industry Bottleneck Scanner

Upstream discovery engine for finding economically important second-/third-order beneficiaries from market-triggered causal research.

The active architecture starts from observable market anomalies, checks whether a concrete structural demand shock is real, expands through evidence-backed value-chain dependencies, and prioritizes nodes where new demand reaches **pre-existing constrained supply** and/or joins **other independent demand roots** before obvious contracts or explosive earnings make the beneficiary widely recognized.

The system does **not** try to predict every quiet industry before the market reacts, does not require complete earnings-call transcript coverage, and does not treat a lagging stock as automatically cheap.

Architecture consolidation is complete. The single source of truth is [`docs/current_roadmap.md`](docs/current_roadmap.md); module ownership and compatibility rules are in [`docs/implementation_compatibility.md`](docs/implementation_compatibility.md). If an older design document conflicts with those files, the current roadmap wins.

## Canonical discovery universe

The discovery universe remains a broad US-listed universe represented as a dated immutable snapshot rather than a hard-coded ticker list. The registry preserves issuer/security identity so market data, SEC identity resolution, disclosures, and later company mapping remain reproducible across ticker changes and share classes.

```text
Broad US universe
  -> EOD / weekly market history
  -> bottom-up industry / economic-cluster breadth
  -> Market Trigger
  -> Causal Diagnosis
  -> Root Demand Shock
  -> Evidence-backed Causal Graph
  -> Pre-shock Industry State Lookup
  -> Independent Demand-root Convergence
  -> Pre-News Chain Selection
  -> Bottleneck / Economic Capture / Reinvestment / Expectation Gap
  -> Listed-company Exposure Mapping
  -> Repo B Underwriting
```

ETF products such as SOXX may later corroborate a market theme, but they are not the canonical industry aggregation unit.

## Two-loop design

The active architecture has two loops.

```text
LOW-FREQUENCY STATE LOOP                 EVENT-DRIVEN MARKET LOOP

public disclosures / physical data       broad-US price / volume history
            |                                         |
            v                                         v
Persistent Industry State                         Market Trigger
            |                                         |
            |                                         v
            |                                  Causal Diagnosis
            |                                         |
            |                                         v
            |                                  Root Demand Shock
            |                                         |
            +----------------------+------------------+
                                   |
                                   v
                         Causal Graph / Expansion
                                   |
                                   v
                         Demand Convergence Engine
                                   |
                     new shock x old bottleneck
                    x independent demand roots
                                   |
                                   v
                         Pre-News Chain Selector
```

This allows the system to recognize cases where a new theme enters a supply chain that was already tight for unrelated reasons.

## Existing scanner work is retained

The original transcript-first implementation is now a reusable **operating-evidence subsystem**, not the top-level discovery architecture.

The following remain canonical and should be reused:

- `SourceDocument` / `AtomicSignal` contracts,
- Capex / Demand / Scarcity / Pricing extraction,
- direction / negation / resolution logic,
- analyst-question exclusion,
- speaker/section/source provenance,
- independent-company aggregation,
- comparable current-vs-baseline acceleration when like-for-like windows exist,
- cache-first collection and validation artifacts.

```text
SourceDocument
  -> local deterministic scanner
  -> AtomicSignal
  -> optional comparable-window acceleration
  -> operating support for Causal Diagnosis
```

Earnings calls remain useful, including older calls that document a condition before the market notices it. They are one source alongside earnings releases, 8-K/10-Q filings, investor presentations, customer/supplier/competitor disclosures, and public physical industry data.

## Historical transcript validation

Frozen validation v1 remains preserved as an Alpha-Vantage-only, source-coverage-limited audit artifact. It is not rewritten to fit the new roadmap.

The later Quartr-centered transcript-v2 draft is **superseded as an active plan**. Quartr adapter/fallback code may remain parked because the technical work is reusable if access changes, but no active market/causal/state module may depend on Quartr availability and complete transcript coverage is no longer a system gate.

See [`docs/v2_validation_contract_draft.md`](docs/v2_validation_contract_draft.md) for the historical supersession note.

## Active implementation modules

Current provider-independent core:

- `massive_universe.py` — cache-first dated common-stock membership and SIC enrichment;
- `market_universe.py` — dated identity/classification join with explicit classification coverage;
- `eod_market_data.py` — cache-first Massive grouped-daily normalization into the existing daily-bar contract;
- `market_history.py` — adjusted daily-bar features with explicit `as_of` safety;
- `market_trigger.py` — bottom-up industry/economic-bucket breadth trigger;
- `market_trigger_artifacts.py` — dated normalized history and versioned market-trigger artifacts;
- `disclosure_documents.py` / `source_scan.py` — source-agnostic normalization through the existing scanner;
- `sec_edgar.py` — cache-first, strict-as-of SEC 8-K/10-Q/10-K and EX-99 adapter;
- `operating_support.py` — freshness/coverage-aware provider-independent operating support;
- `causal_diagnosis.py` — market trigger + operating-support diagnosis;
- `causal_expansion.py` — pre-news research-priority scoring and gates;
- `causal_graph.py` — append-only evidence-backed dependency edges;
- `root_demand_shock.py` / `causal_orchestration.py` — evidence-gated roots and as-of path/convergence artifacts;
- `industry_state.py` — append-only pre-shock supply-state memory;
- `industry_state_updater.py` — explicit issuer-to-node mapping plus evidence-diverse state updates;
- `demand_convergence.py` — new-shock x pre-shock constraint x independent-root convergence.

Raw full transcripts are not sent to an LLM. Cheap deterministic work remains local-first; later model calls are reserved for already-filtered research tasks and cannot approve causal evidence by themselves.

## Responsibility boundary

Repo A owns:

- broad-US universe normalization/provenance,
- market-trigger detection,
- source/document normalization,
- operating-signal extraction,
- persistent industry state,
- causal/value-chain graph and evidence approval,
- demand convergence,
- bottleneck/economic-capture research ranking,
- listed-company exposure mapping,
- a small thesis manifest for downstream underwriting.

Repo A does **not** own full financial underwriting, DCF, final valuation, or final investment reports. Those remain in `investment-research-automation` (Repo B), which stays untouched until the upstream manifest is stable.

## Current development sequence

Architecture consolidation / legacy-boundary work is **complete**. The active sequence is now:

1. bootstrap `broad_us_common_stocks_v1` from Massive reference data;
2. generate real broad-US bottom-up Market Trigger artifacts from 2024-11-01 onward;
3. ingest earnings releases / SEC filings / presentations into existing evidence contracts;
4. add provider-independent operating-support and industry-state update jobs;
5. persist root-demand-shock/path artifacts and integrate the existing causal graph/convergence cores;
6. replay an early AI-cycle case with frozen `as_of` timestamps and later confirmation held out;
7. map listed-company exposure;
8. freeze the Repo-A -> Repo-B thesis manifest only after upstream validation;
9. add production cadence only after the replay and handoff boundary are stable.

Do not extend the frozen transcript `validation_*` workflow into the new end-to-end product path. The new historical replay will get a separate orchestration/validation entry point.

## Commands

Install the package in editable mode:

```bash
pip install -e .
```

Build or resume the dated canonical universe. The default pacing is compatible with the
Massive Stocks Basic five-calls-per-minute limit. Validated raw responses are checkpointed;
rerunning the command continues with uncached tickers.

```bash
export MASSIVE_API_KEY="..."
ibs-massive-universe \
  --as-of 2026-08-21 \
  --cache-dir var/cache/massive-reference \
  --output-csv var/universe/as_of=2026-08-21/market_universe.csv \
  --manifest var/universe/as_of=2026-08-21/manifest.json \
  --max-overview-requests 1000
```

Once the manifest has no pending overview requests, run the Phase-1 market path. `IWB` is
used only as the broad-market benchmark; company membership, not an ETF, defines each
industry bucket.

```bash
export MASSIVE_API_KEY="..."
ibs-market-trigger \
  --universe-csv var/universe/as_of=2026-08-21/market_universe.csv \
  --universe-as-of 2026-08-21 \
  --universe-source "Massive reference v3 dated snapshot" \
  --as-of 2026-08-21 \
  --start-date 2024-11-01 \
  --benchmark IWB \
  --cache-dir var/cache/massive-grouped-daily \
  --output-dir artifacts/market-trigger \
  --request-interval-seconds 13
```

The initial backfill is provider-quota-sensitive. Raw daily responses are cached by date,
so normal incremental EOD runs fetch only uncached dates. Outputs are written below an
`as_of=YYYY-MM-DD` directory and include explicit missing/insufficient-history coverage;
the cohort is never silently shrunk.

Replay the persisted normalized history without calling the provider:

```bash
ibs-market-trigger-replay \
  --history-jsonl artifacts/market-trigger/as_of=2026-08-21/market_history.jsonl \
  --as-of 2026-06-30 \
  --output artifacts/market-trigger/replay-2026-06-30.json
```

Produce a provider-free monthly calibration series from the same frozen archive. The command
selects the last available benchmark session in each month, applies the dated universe cutoff,
and records per-date eligibility and output hashes without tuning the policy thresholds:

```bash
ibs-market-trigger-calibrate \
  --history-jsonl artifacts/market-trigger/as_of=2026-08-21/market_history.jsonl \
  --start-as-of 2025-05-30 \
  --end-as-of 2026-08-21 \
  --output-dir artifacts/market-trigger/calibration
```

Collect trigger-scoped SEC disclosures. SEC does not require an API key, but its fair-access
policy requires a declared organization/contact User-Agent:

```bash
export SEC_USER_AGENT="Research Project contact@example.com"
ibs-sec-disclosures \
  --companies-csv artifacts/trigger-companies.csv \
  --since 2024-11-01 \
  --as-of 2026-08-21T23:59:59+00:00 \
  --cache-dir var/cache/sec-edgar \
  --output-jsonl artifacts/operating/disclosures.jsonl \
  --diagnostics artifacts/operating/sec-collection.json
```

See [`docs/source_agnostic_operating_evidence.md`](docs/source_agnostic_operating_evidence.md)
for the normalization, freshness, coverage, and replay contracts.

Update append-only economic-node state from issuer signals and optional external observations:

```bash
ibs-industry-state-update \
  --atomic-signals-jsonl artifacts/operating/atomic_signals.jsonl \
  --node-assignments-csv artifacts/research/company_node_assignments.csv \
  --observations-jsonl artifacts/industry/physical_observations.jsonl \
  --as-of 2026-08-21T23:59:59+00:00 \
  --registry artifacts/industry/industry_state.jsonl \
  --decisions artifacts/industry/state_update_decisions.json
```

See [`docs/industry_state_update_contract.md`](docs/industry_state_update_contract.md).

Record an evidence-gated Root Demand Shock and traverse approved graph/state history:

```bash
ibs-root-shock-append \
  --input artifacts/causal/root_shock_input.json \
  --registry artifacts/causal/root_shocks.jsonl

ibs-causal-convergence \
  --root-shock-registry artifacts/causal/root_shocks.jsonl \
  --causal-graph-registry artifacts/causal/graph.jsonl \
  --industry-state-registry artifacts/industry/industry_state.jsonl \
  --trigger-root-shock-id ai-inference-deployment-2026q3 \
  --as-of 2026-08-21T23:59:59+00:00 \
  --output-dir artifacts/causal/convergence
```

See [`docs/causal_convergence_contract.md`](docs/causal_convergence_contract.md).

Run the separate frozen historical pre-news replay after supplying explicit research judgments
for every promoted convergence node. The runner fingerprints every input and rejects later
confirmation leakage; it does not infer economic-capture or expectation-gap scores.

```bash
ibs-pre-news-replay \
  --input artifacts/replay/early-ai-electrical/input.json \
  --market-trigger-artifact artifacts/market-trigger/replay-2024-11-15.json \
  --root-shock-registry artifacts/causal/root_shocks.jsonl \
  --causal-graph-registry artifacts/causal/graph.jsonl \
  --industry-state-registry artifacts/industry/industry_state.jsonl \
  --output-dir artifacts/replay/early-ai-electrical/output
```

See [`docs/historical_pre_news_replay.md`](docs/historical_pre_news_replay.md).

Legacy bounded transcript workflows remain available for regression/audit work:

```text
ibs-transcript-collect
ibs-pilot-diagnostics
ibs-phase1-batch
ibs-phase1-pilot
ibs-phase1-validate
ibs-review-language
```

They should not be interpreted as the top-level current product workflow.

See also [`docs/architecture.md`](docs/architecture.md), [`docs/current_roadmap.md`](docs/current_roadmap.md), [`docs/implementation_status.md`](docs/implementation_status.md), [`docs/implementation_compatibility.md`](docs/implementation_compatibility.md), [`docs/market_trigger_contract.md`](docs/market_trigger_contract.md), [`docs/market_triggered_causal_discovery.md`](docs/market_triggered_causal_discovery.md), [`docs/historical_pre_news_replay.md`](docs/historical_pre_news_replay.md), and [`docs/signal_taxonomy.md`](docs/signal_taxonomy.md).
