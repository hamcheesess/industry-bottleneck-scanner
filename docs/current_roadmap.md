# Current roadmap — market-triggered causal bottleneck discovery

Status: **active design source of truth** for Repo A. Architecture consolidation is complete. Frozen transcript validation v1 remains an audit artifact; the old Quartr-centered transcript-v2 draft is historical only.

## Objective

Repo A should discover economically important second- and third-order beneficiaries without requiring real-time news speed or complete transcript coverage.

The operating idea is:

```text
observable market reaction
  -> identify the concrete root demand shock
  -> verify that the shock is economically real
  -> traverse evidence-backed value-chain dependencies
  -> look up supply conditions that were already known before the shock
  -> prefer downstream nodes where several independent demand roots converge
  -> rank bottleneck strength, economic capture, reinvestment runway, and expectation gap
  -> map listed-company exposure
  -> hand a small thesis manifest to Repo B
```

The highest-priority setup is not merely `new demand -> beneficiary`. It is:

```text
new demand shock
  x pre-existing supply constraint
  x independent demand-root convergence
  x strong economic capture
  x still-open expectation gap
```

## Architectural rule: preserve useful old layers, change their role

The old transcript-first Phase-1 implementation is not deleted. Its reliable components become reusable operating-evidence infrastructure:

- `SourceDocument` and `AtomicSignal` remain the canonical local issuer-evidence/signal contracts.
- Capex / Demand / Scarcity / Pricing scanners remain the operating-language extractor.
- direction, negation, resolution, speaker-role exclusion, provenance, and evidence timestamps remain correctness invariants.
- current-vs-baseline aggregation remains available for operating acceleration when comparable windows exist.
- cache-first collection, fingerprints, validation artifacts, and frozen-v1 results remain auditable.

What changes is the dependency direction: transcript completeness no longer gates discovery, and operating acceleration is one input to causal diagnosis rather than the entire discovery engine.

## Canonical pipeline

### Loop A — persistent low-frequency industry state

Run independently of market triggers and update only when public evidence changes.

```text
public disclosures / physical data / operating evidence
  -> normalized evidence
  -> economically meaningful node identity
  -> supply-state assessment
  -> append-only IndustryStateSnapshot history
```

State dimensions:

- supply inelasticity,
- lead-time pressure,
- capacity tightness,
- capacity-expansion difficulty,
- qualification barriers,
- pricing pressure.

Historical safety rule: a later market trigger may only use a state snapshot timestamped strictly before that trigger.

### Loop B — event-driven market discovery

```text
broad US universe
  -> end-of-day / weekly market history
  -> bottom-up industry/economic-cluster breadth
  -> Market Trigger
  -> Causal Diagnosis
  -> Root Demand Shock
```

ETF products may corroborate a market theme but are not the canonical aggregation unit. Canonical market aggregation starts from company membership in sector / industry / economic-subcluster buckets.

### Join — evidence-backed causal expansion

```text
Root Demand Shock
  -> approved causal graph edges
  -> reachable value-chain nodes
  -> pre-shock state lookup
  -> independent demand-root convergence
  -> Pre-News Chain Selector
```

An LLM may propose a causal edge but cannot approve it. Approval requires an explicit economic mechanism, independent evidence classes, external corroboration, and look-ahead-safe timestamps.

### Final Repo-A research layers

```text
priority convergence
  -> bottleneck assessment
  -> economic capture
  -> reinvestment runway
  -> expectation gap
  -> listed-company exposure mapping
  -> small thesis manifest
```

Repo A stops before financial underwriting, valuation, DCF, or a final investment judgment.

### Repo B boundary

Repo B remains unchanged until Repo A produces stable candidate manifests:

```text
candidate thesis manifest
  -> local financial gate
  -> financial-risk filter
  -> company deep research
  -> DCF
  -> final report
```

## Canonical integration boundary

The architecture must be assembled by composition, not by rewriting legacy modules into one giant pipeline.

```text
provider adapters
   |-- market bars ----------------------> market_history -> market_trigger
   |
   |-- issuer documents -> SourceDocument -> existing scanner -> AtomicSignal
   |                                                  |             |
   |                                                  |             +-> operating support
   |                                                  +----------------> state evidence
   |
   `-- physical / industry data -> CausalEvidence ---------------------> state / graph evidence

market trigger + normalized operating support
   -> causal diagnosis
   -> root-demand-shock artifact
   -> causal graph traversal
   -> pre-shock state lookup
   -> demand convergence
   -> pre-news node ranking
   -> company exposure mapping
```

Provider-specific code must stay below normalization. Causal/state/ranking modules must never import Alpha Vantage, Quartr, SEC transport, or a price vendor directly.

The future top-level orchestration layer should call the existing modules through stable contracts. Do **not** physically move or rename the mature scanner/validation modules merely to make the directory tree match the new conceptual architecture; that would create unnecessary import/CLI churn.

## Current implementation checkpoint

This is the code status after architecture consolidation.

| Layer | Current status | Reused / implemented pieces | Missing before real execution |
|---|---|---|---|
| Universe / identity | **REUSE + MARKET JOIN IMPLEMENTED** | dated broad-US universe contracts, issuer/security identity, dated sector/bucket classification join with explicit unclassified denominator | production membership/classification snapshot and refresh path |
| Transcript evidence | **REUSE OPTIONAL** | Alpha Vantage adapter, cache, transcript normalization, analyst exclusion | no universal transcript fallback required |
| Operating scanner | **KEEP + GENERIC PATH EXECUTABLE** | `SourceDocument`, `AtomicSignal`, four scanners, generic disclosure normalization/scanning, analyst exclusion | real trigger-scoped source artifacts |
| Frozen transcript validation | **FROZEN** | v1 audit trail and regression lessons | nothing; do not retrofit |
| Quartr-era v2 | **PARKED** | adapter/fallback/provenance code and tests | no active work unless access situation changes |
| Market features | **EXECUTABLE / CALIBRATION PENDING** | `market_history.py`, explicit `as_of` features, Massive grouped-daily adjusted adapter, self-contained cache-first normalized history archive | production universe run and provider entitlement/retention verification |
| Market trigger | **EXECUTABLE / CALIBRATION PENDING** | `market_trigger.py`, bottom-up breadth, dated v1 trigger artifact, live CLI and strict-as-of replay CLI | real historical calibration and trigger-quality assessment |
| Causal diagnosis | **PROVIDER-INDEPENDENT BOUNDARY IMPLEMENTED** | freshness-aware `OperatingSupport`, one-sided evidence, optional old `AccelerationSnapshot` | real source coverage calibration |
| Causal graph | **ORCHESTRATION EXECUTABLE / REAL EVIDENCE PENDING** | edge approval/history, append-only Root Demand Shock approval, bounded path expansion, `DemandBranch` artifacts | real root/edge evidence |
| Pre-shock industry state | **UPDATER EXECUTABLE / REAL EVIDENCE PENDING** | append-only snapshots, strict pre-trigger lookup, explicit company-to-node assignments, AtomicSignal/external observation updater, diversity gate | real node assignments and physical/industry observations |
| Demand convergence | **ORCHESTRATION EXECUTABLE / REAL EVIDENCE PENDING** | root deduplication, strict pre-shock constraint join, versioned convergence artifacts | real graph/state integration and replay calibration |
| Pre-news node ranking | **CORE IMPLEMENTED** | `causal_expansion.py`, six dimensions + hard gates | real-data scoring policy validation |
| Company exposure mapping | **NOT IMPLEMENTED** | boundary defined | node-to-company exposure model and evidence contract |
| Repo-A -> Repo-B manifest | **NOT FROZEN** | conceptual boundary only | implement only after upstream historical replay works |

This table is the implementation checkpoint. New work should advance the next missing column rather than create parallel replacements for already working contracts.

## Source strategy

There is no longer a requirement to solve universal earnings-call transcript coverage.

Preferred evidence hierarchy is purpose-specific rather than a single fallback chain:

- earnings calls: management operating language when available;
- earnings releases / 8-K / 10-Q: first-party operating and financial evidence;
- investor presentations: capacity, product, market, and capex context;
- customer / supplier / competitor disclosures: triangulation and causal-edge support;
- public physical / industry data: supply-state and demand-state corroboration;
- price/volume history: market trigger and expectation-attention inputs.

A missing transcript is therefore `source unavailable`, not a negative operating signal and not a system-wide blocker.

The existing Alpha Vantage transcript adapter and normalized cache remain usable. Quartr adapter/fallback code is parked as an experimental adapter because usable API access is unavailable; active architecture must not depend on it.

## Operating evidence freshness

A market trigger does not require a same-day earnings call. Older evidence remains useful if interpreted correctly.

At trigger time `T`, operating evidence is separated into:

1. **pre-existing operating state** — prior earnings calls/releases/10-Qs;
2. **since-last-earnings updates** — 8-Ks, presentations, capacity/capex announcements, customer/supplier disclosures;
3. **trigger-era catalyst evidence** — information plausibly connected to the immediate market move.

Older earnings calls may prove that a condition existed before the market reacted; they must not be mislabeled as the immediate trigger cause.

## Development phases

### Phase 0 — architecture consolidation — COMPLETE

Goal: one active roadmap and explicit compatibility boundaries.

Completed:

- frozen v1 remains frozen and auditable;
- Quartr-centered transcript-v2 is explicitly superseded as the active plan;
- old scanner/transcript code has KEEP / REUSE / FROZEN / PARKED roles;
- active modules are prohibited from depending on parked Quartr-era provider code;
- active policy, architecture docs, README, compatibility map, and regression tests agree on one control flow;
- Repo B remains untouched.

Exit condition is satisfied. Further architecture changes must update this roadmap and compatibility contract before code is redirected.

### Phase 1 — real market trigger — IN PROGRESS

Goal: generate real bottom-up market triggers from broad-US end-of-day history.

Implementation:

- **DONE:** adopt `broad_us_common_stocks_v1` instead of licensed Russell 3000 membership;
- **DONE:** add a cache-first Massive reference adapter for dated common-stock membership,
  CIK/FIGI identity, explicit SEC-SIC classification, and free-plan batch resume;
- **DONE:** connect Massive grouped-daily adjusted US-stock bars through a cache-first adapter to `market_history.py`;
- map universe companies into sector / industry / economic-subcluster buckets;
- **DONE:** compute market-relative and bottom-up sector-relative breadth;
- **DONE:** persist normalized history plus dated, versioned `IndustryMarketTrigger` artifacts with explicit coverage diagnostics;
- **DONE:** enforce strict `as_of` in feature calculation and dated artifact paths;
- **DONE:** preserve dated universe provenance/classification gaps and support provider-free strict-as-of replay from normalized history;
- **IN PROGRESS:** enrich the frozen `2026-08-21` production snapshot, backfill from
  `2024-11-01`, and calibrate thresholds through valid dated historical trigger replay.

No LLM is required.

### Phase 2 — source-agnostic operating evidence — IN PROGRESS

Goal: stop relying on transcript completeness while reusing the existing scanner.

Implementation:

- **DONE:** normalize earnings release / 8-K / 10-Q / presentation text into `SourceDocument`;
- **DONE:** add a cache-first, strict-`as_of` SEC submissions/archive adapter for 8-K, 10-Q,
  10-K, and 8-K `EX-99.*` exhibits;
- **DONE:** retain transcript path as an optional high-quality source;
- **DONE:** run the existing deterministic scanner over all eligible document types;
- **DONE:** add source freshness / coverage diagnostics;
- **DONE:** keep analyst-question exclusion where speaker structure exists;
- **DONE:** introduce one provider-independent `OperatingSupport` boundary for causal diagnosis;
- **IN PROGRESS:** exercise SEC collection on the first real trigger-scoped company set and
  measure non-SEC IR/presentation coverage gaps before deciding whether another adapter is needed.

The existing comparable current-vs-baseline engine remains available where like-for-like windows exist. `OperatingSupport` should be an adapter/output contract, not a replacement for `AtomicSignal` or `AccelerationSnapshot`.

### Phase 3 — persistent industry-state updater — IN PROGRESS

Goal: build a reusable memory of pre-shock bottlenecks.

Implementation:

- **DONE:** define stable economic-node IDs independent of tickers and require explicit
  many-to-many company-to-node assignments;
- **DONE:** derive candidate state observations from eligible AtomicSignals and accept the same
  observation contract from external physical evidence;
- **DONE:** require both evidence-class and source-entity diversity before a known state is recorded;
- **DONE:** append snapshots rather than overwrite and reject duplicate `(node_id, as_of)` keys;
- **IN PROGRESS:** supply real node assignments and public physical/industry observations;
- add decay/staleness rules later only after replay evidence justifies them.

### Phase 4 — causal graph and demand convergence integration — IN PROGRESS

Goal: find the points where branches become a common constrained trunk.

Implementation:

- **DONE:** persist explicit, evidence-gated root-demand-shock revisions;
- **DONE:** use the existing append-only approved graph-edge store at an exact `as_of`;
- **DONE:** traverse depth-bounded, cycle-safe paths;
- **DONE:** convert paths to stable `DemandBranch` artifacts;
- **DONE:** deduplicate paths sharing one root shock for convergence breadth;
- **DONE:** join each target node with the latest strictly pre-trigger state;
- **DONE:** rank `pre_shock_bottleneck`, `multi_branch_convergence`, and `priority_convergence`;
- **IN PROGRESS:** feed real promoted nodes into the existing pre-news node assessment and
  calibrate using the frozen historical replay.

### Phase 5 — historical pre-news replay

First serious case: early AI-cycle causal expansion into data-center/electrical infrastructure.

Freeze before running:

- market-trigger date,
- root demand-shock definition,
- evidence cutoff,
- pre-shock state snapshots,
- graph-edge evidence,
- later obvious confirmation events held out.

Primary question: could the system reach the economically important downstream node using only information available at that time?

Secondary questions: how early, with what evidence diversity, and with what market-attention gap? Later stock returns are diagnostic, not the primary correctness target.

### Phase 6 — company exposure mapping

Only after node-level discovery works:

- product/revenue exposure,
- owned capacity,
- qualification position,
- competitive position,
- capacity expansion ability,
- participation in the identified bottleneck.

Relative underperformance alone is never sufficient.

### Phase 7 — Repo-A to Repo-B contract

Freeze a small manifest only after the upstream path is stable. Do not pass Repo A's internal graphs or every evidence artifact downstream.

Candidate manifest should contain at minimum:

- theme / root demand shock,
- causal path,
- target node,
- pre-shock state reference,
- convergence summary,
- bottleneck / capture / reinvestment / expectation assessments,
- company exposure reason,
- evidence references and `as_of` timestamp.

Then connect to Repo B without changing Repo B's underwriting semantics.

### Phase 8 — production cadence

Only after historical replay and the handoff contract are stable:

- EOD/weekly market sensing over the broad universe;
- incremental public-disclosure ingestion;
- append-only industry-state updates;
- graph evidence updates when new evidence changes an edge;
- deep causal/company research only for triggered or convergent nodes;
- cache-first/local-first execution and bounded paid-model usage.

## Validation roadmap

The old transcript-v2 validation plan is no longer the active system validation contract. Its useful extraction tests may be reused as subsystem tests.

The active system needs separate gates for:

1. market-trigger quality and breadth;
2. operating-evidence extraction correctness;
3. causal-edge correctness;
4. pre-shock state correctness and look-ahead safety;
5. independent-root convergence correctness;
6. pre-news node ranking quality;
7. listed-company exposure mapping;
8. end-to-end historical replay without post-event leakage.

Do not extend the old `validation_*` CLI family into the new end-to-end architecture. When historical market-triggered replay becomes executable, create a separate replay/validation entry point that consumes the new normalized artifacts while leaving frozen-v1 CLIs unchanged.

Thresholds remain draft until historical cases are frozen before outcomes are inspected.

## Non-goals

- high-frequency or intraday trading;
- winning by seconds on headline ingestion;
- complete transcript coverage as a prerequisite;
- universe-scale LLM analysis;
- automatic approval of LLM-generated causal stories;
- treating price momentum as a thesis;
- treating lagging stocks as cheap;
- allowing later contracts/earnings to define an earlier bottleneck;
- DCF or investment verdicts in Repo A.
