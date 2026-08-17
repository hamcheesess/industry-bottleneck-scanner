# Industry Bottleneck Scanner

Upstream discovery engine for finding economically important second-/third-order beneficiaries from market-triggered causal research.

The active architecture starts from observable market anomalies, checks whether a concrete structural demand shock is real, expands through evidence-backed value-chain dependencies, and prioritizes nodes where new demand reaches **pre-existing constrained supply** and/or joins **other independent demand roots** before obvious contracts or explosive earnings make the beneficiary widely recognized.

The system does **not** try to predict every quiet industry before the market reacts, does not require complete earnings-call transcript coverage, and does not treat a lagging stock as automatically cheap.

The canonical roadmap is [`docs/current_roadmap.md`](docs/current_roadmap.md). The module migration/compatibility rules are [`docs/implementation_compatibility.md`](docs/implementation_compatibility.md).

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

- `market_history.py` — adjusted daily-bar features with explicit `as_of` safety;
- `market_trigger.py` — bottom-up industry/economic-bucket breadth trigger;
- `causal_diagnosis.py` — market trigger + operating-support compatibility bridge;
- `causal_expansion.py` — pre-news research-priority scoring and gates;
- `causal_graph.py` — append-only evidence-backed dependency edges;
- `industry_state.py` — append-only pre-shock supply-state memory;
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

1. consolidate the active architecture and legacy boundaries;
2. connect free/low-cost EOD adjusted price history;
3. generate real bottom-up market triggers;
4. ingest source-agnostic public disclosures into the existing evidence contracts;
5. update persistent industry-state snapshots;
6. persist root-demand shocks and approved causal paths;
7. replay an early AI-cycle case with frozen `as_of` timestamps and later confirmation held out;
8. map listed-company exposure;
9. freeze the Repo-A -> Repo-B thesis manifest only after upstream validation.

## Commands

Install the package in editable mode:

```bash
pip install -e .
```

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

See also [`docs/architecture.md`](docs/architecture.md), [`docs/current_roadmap.md`](docs/current_roadmap.md), [`docs/implementation_compatibility.md`](docs/implementation_compatibility.md), [`docs/market_triggered_causal_discovery.md`](docs/market_triggered_causal_discovery.md), and [`docs/signal_taxonomy.md`](docs/signal_taxonomy.md).
