# Architecture

## Active goal

Repo A is an upstream **market-triggered causal bottleneck discovery engine**.

It does not try to predict every quiet industry before the market reacts and it no longer requires complete transcript coverage. It starts from a broad market anomaly, determines whether there is a real economic demand shock behind it, expands through evidence-backed value-chain dependencies, and looks for downstream nodes where new demand collides with pre-existing supply constraints and other independent demand roots.

The active roadmap is [`current_roadmap.md`](current_roadmap.md). Module-by-module compatibility rules are in [`implementation_compatibility.md`](implementation_compatibility.md).

## Canonical flow

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
  -> Repo B thesis manifest
```

A particularly important setup is:

```text
new demand shock
  x pre-existing constrained supply
  x multiple independent demand roots converging on the same node
```

The system is intentionally many-to-many. One root demand shock can branch into several dependencies, and one downstream node can receive demand from several unrelated roots.

## Two-loop architecture

### Loop A: low-frequency persistent industry state

Runs independently of market triggers.

```text
public operating evidence / physical data
  -> normalized evidence
  -> economic value-chain node
  -> supply-state assessment
  -> append-only IndustryStateSnapshot history
```

Tracked state includes:

- supply inelasticity,
- lead-time pressure,
- capacity tightness,
- capacity-expansion difficulty,
- qualification barriers,
- pricing pressure.

Historical replay must use only snapshots timestamped before the later trigger.

### Loop B: event-driven market discovery

```text
Russell-3000-like broad US universe
  -> company-level price / volume features
  -> sector / industry / economic-subcluster breadth
  -> Market Trigger
  -> operating-evidence diagnosis
  -> concrete Root Demand Shock
```

ETF products may corroborate market themes but are not the canonical aggregation unit.

### Join: causal expansion and convergence

```text
Root Demand Shock
  + approved economic dependency graph
  + strictly pre-trigger industry state
  + other independent demand roots
  -> convergence assessment
  -> pre-news research priority
```

An LLM may propose graph edges later, but it cannot approve them. Approval requires explicit mechanism, independent evidence, external corroboration, and look-ahead-safe provenance.

## Canonical discovery universe

Repo A retains the broad US-listed universe contract, represented as a dated immutable snapshot with issuer/security identity and source identifiers.

```text
membership snapshot
  -> normalize tickers / share classes
  -> preserve issuer_id + security_id
  -> resolve source identities such as SEC CIK
  -> market / disclosure ingestion
```

Unresolved identifiers remain explicit rather than being silently dropped.

## Industry aggregation versus causal nodes

These are deliberately different layers.

### Market / operating aggregation

Use sector, industry, subindustry, or explicitly defined economic subclusters to measure broad participation across companies.

This layer answers:

> Is a meaningful group of companies moving or showing similar operating evidence?

### Causal/value-chain node

After a trigger is diagnosed, the system may create finer economic nodes such as `large-power-transformers`, `data-center-switchgear`, or `AI-inference-host-CPU`.

This layer answers:

> Through which physical/economic dependencies must the new demand propagate?

A causal node must not be silently substituted for static industry classification in the Market Trigger layer.

## Existing operating scanner: retained subsystem

The original Phase-1 transcript-first work remains useful and is not being rewritten away.

```text
SourceDocument
  -> lexical / regex + optional local semantic retrieval
  -> deterministic adjudication
  -> AtomicSignal
  -> optional current-vs-baseline aggregation / acceleration
```

Retained correctness invariants include:

- direction,
- negation,
- resolution,
- analyst-question exclusion,
- source section / speaker provenance,
- independent-company breadth,
- real timestamps,
- no raw full-transcript LLM requirement.

Earnings-call transcripts are now one operating-evidence source rather than the top-level discovery gate.

## Source strategy

No single universal fallback provider is required.

Purpose-specific evidence sources may include:

- earnings calls when available,
- earnings releases,
- 8-K / 10-Q filings,
- investor presentations,
- customer / supplier / competitor disclosures,
- public physical and industry data,
- adjusted daily market history.

Missing transcript coverage is a source limitation, not negative evidence and not a reason to shrink a market-discovery cohort silently.

Alpha Vantage transcript collection/cache code remains reusable. Quartr adapter/fallback work is parked as an optional historical experiment because usable API access is unavailable; active market/causal/state code must not depend on it.

## Operating evidence timing

At a market trigger time `T`, older documents can still be useful but their role must be explicit:

1. **pre-existing operating state** — what was already true before the market moved;
2. **since-last-earnings updates** — new public operating/capacity information after the last regular report;
3. **trigger-era catalyst evidence** — evidence plausibly connected to the immediate market move.

A two-month-old earnings call may be strong pre-news evidence. It must not be mislabeled as proof of the immediate trigger cause.

## Current active modules

- `market_history.py` — provider-independent EOD feature calculation and `as_of` safety;
- `market_trigger.py` — bottom-up market breadth trigger;
- `disclosure_documents.py` / `source_scan.py` — provider-neutral issuer disclosures through the existing scanner;
- `sec_edgar.py` — cache-first SEC adapter below `PublicDisclosure` normalization;
- `operating_support.py` — freshness/coverage-aware one-sided evidence plus optional comparable acceleration;
- `causal_diagnosis.py` — market trigger plus provider-independent operating support;
- `causal_expansion.py` — demand transmission / bottleneck / capture / reinvestment / triangulation / expectation-gap ranking;
- `causal_graph.py` — append-only edge approval history and bounded traversal;
- `industry_state.py` — append-only pre-shock node-state memory;
- `industry_state_updater.py` — explicit node mapping and evidence-diverse state observations;
- `demand_convergence.py` — new-shock x pre-shock constraint x independent-root convergence.

`causal_diagnosis.py` still accepts the older `AccelerationSnapshot` interface for compatibility,
but the active path now consumes `OperatingSupport`. It can therefore classify fresh one-sided
evidence and since-last-earnings updates without requiring perfect transcript pairs.

## Historical artifacts and frozen work

### Frozen validation v1

Frozen v1 remains an Alpha-Vantage-only transcript experiment and audit trail. It is not modified to fit the new architecture.

### Old transcript-v2 / Quartr draft

The Quartr-centered multi-source transcript-v2 plan is superseded as an active roadmap because usable API access is unavailable and complete transcript coverage is no longer a system prerequisite.

Its useful ideas remain reusable subsystem principles:

- source provenance,
- no silent cohort shrinkage,
- comparable-source caution,
- extraction correctness tests,
- look-ahead-safe validation.

The adapter and tests may remain parked without becoming active dependencies.

## Repo boundary

### Repo A: `industry-bottleneck-scanner`

Owns:

- broad-US discovery universe and classifications,
- market triggers,
- operating-evidence extraction,
- persistent industry state,
- causal/value-chain graph,
- demand convergence,
- bottleneck/economic-capture research priority,
- listed-company exposure mapping,
- small thesis manifests.

Must not own:

- DCF,
- final valuation,
- full company underwriting,
- final investment recommendation.

### Repo B: `investment-research-automation`

Retains:

```text
candidate thesis manifest
  -> local financial gate
  -> financial-risk filter
  -> ranked queue
  -> company deep research
  -> DCF
  -> final report
```

Repo B remains untouched until the upstream manifest is stable.

## Active development sequence

1. architecture consolidation and legacy compatibility boundaries;
2. real free/low-cost EOD market-history ingestion;
3. real bottom-up industry/economic-cluster Market Trigger artifacts;
4. source-agnostic public-disclosure ingestion into existing evidence contracts;
5. persistent industry-state update jobs;
6. root-demand-shock and causal-path persistence;
7. early-AI-cycle historical replay with frozen `as_of` dates;
8. company exposure mapping;
9. Repo-A -> Repo-B manifest freeze and integration.

## Design principles

### Market-triggered, not headline-speed

The system may run end-of-day or weekly. It aims to reason better about second-/third-order propagation, not win a seconds-level news race.

### New demand x old bottleneck

A new theme is especially interesting when it enters a node whose supply was already constrained for unrelated reasons.

### Convergence over simplistic chains

Prefer shared trunks where several independent roots create demand. Multiple paths from the same root are deduplicated.

### Evidence before narrative

LLM-generated or human-generated value-chain stories remain hypotheses until source-backed edges and states support them.

### Preserve historical knowledge

State and graph histories are append-only so earlier `as_of` decisions can be replayed without hindsight.

### Independent-company breadth over mention count

Repeated evidence from one issuer does not substitute for independent corroboration.

### Local-first cost control

Cheap deterministic market calculations, extraction, aggregation, graph/state logic, and caching run locally. Expensive model calls are reserved for already-filtered research tasks.

### No silent investment inference

Repo A ranks research opportunities and economic exposure. It does not declare a stock investable at a given price.
