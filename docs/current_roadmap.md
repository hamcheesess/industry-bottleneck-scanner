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
| Operating scanner | **KEEP + REAL TRIGGER-SCOPED RUN COMPLETE** | `SourceDocument`, `AtomicSignal`, four scanners, generic disclosure normalization/scanning, analyst exclusion; 479 issuers and 22,863 SEC disclosures normalized at `2026-08-21` | calibrate non-SEC corroboration only where root-shock research requires it |
| Frozen transcript validation | **FROZEN** | v1 audit trail and regression lessons | nothing; do not retrofit |
| Quartr-era v2 | **PARKED** | adapter/fallback/provenance code and tests | no active work unless access situation changes |
| Market features | **EXECUTABLE / CALIBRATION PENDING** | `market_history.py`, explicit `as_of` features, Massive grouped-daily adjusted adapter, self-contained cache-first normalized history archive | production universe run and provider entitlement/retention verification |
| Market trigger | **CALIBRATED / RESEARCH QUEUE READY** | bottom-up breadth, strict-as-of 16-date calibration, outcome-blind stability review, deterministic SEC issuer batches | operating-evidence validation of persistent buckets |
| Causal diagnosis | **REAL PROVIDER-INDEPENDENT RUN COMPLETE** | freshness-aware `OperatingSupport`, one-sided evidence, optional old `AccelerationSnapshot`; 28 dated bucket diagnoses, bounded research packets, and the first strict-as-of eligible research result | investigate remaining concrete mechanisms and external corroboration without automatic approval |
| Causal graph | **ORCHESTRATION EXECUTABLE / TWO INDEPENDENT ROOTS READY** | append-only approval for AI load and grid-modernization roots, three production branches reaching grid interconnection and large-power transformers, bounded expansion, `DemandBranch` artifacts | additional value-chain branches only where independently evidenced |
| Pre-shock industry state | **UPDATER EXECUTABLE / FIRST CONSTRAINED NODE READY** | append-only snapshots, strict pre-trigger lookup, source-diverse grid-interconnection snapshot, severely constrained large-power-transformer snapshot, explicit company-to-node assignments, AtomicSignal/external observation updater | replay calibration and later decay policy |
| Demand convergence | **TWO-ROOT PRODUCTION CALIBRATION COMPLETE** | exact production run, evidence-disjoint root validation, three branches, strict pre-shock join, fail-closed grid node, transformer 75.07 `priority_convergence` | later-confirmation calibration and additional historical cases |
| Pre-news node ranking | **TWO-ROOT REPLAY COMPLETE / CALIBRATION CONTINUES** | six dimensions + hard gates, promoted-convergence join, explicit frozen judgments; transformer remains 73.0 `evidence_backed` despite higher structural convergence | economic-capture and expectation-gap validation |
| Historical pre-news replay | **TWO-ROOT CASE COMPLETE / NARRATIVE GATE ACTIVE** | exact `as_of`, five input fingerprints, 17 dated evidence records across eight classes, mandatory evidence-bound Korean analysis explaining both independent demand paths | explicit later-confirmation holdouts before company mapping |
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
- **DONE:** separate historical `universe_as_of` from the later `market_as_of` archive cutoff so
  calibration never uses a future membership snapshot;
- **DONE:** build the first strict historical snapshot with
  `universe_as_of=2025-05-30`, `market_as_of=2026-08-21`, and history beginning `2024-11-01`;
- **DONE:** produce a provider-free 16-date monthly calibration series with explicit per-date
  eligibility, frozen thresholds, artifact hashes, and no post-cutoff bars;
- **DONE:** classify latest triggers without outcome data into 28 persistent and 22 emerging
  buckets, preserving all 50 results and leaving thresholds frozen;
- **DONE:** join the 28 persistent buckets to 479 unique SEC issuers in five bounded batches;
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
- **DONE:** collect the first real trigger-scoped set: 479 issuers, 13,878 filings, and 22,863
  SEC disclosures with zero collection failures;
- **DONE:** normalize 77,749 section documents, extract 7,135 `AtomicSignal` records, and build
  strict-as-of `OperatingSupport` for all 28 persistent buckets at 94.55% mean fresh coverage;
- **DONE:** join all 28 supports to the frozen market trigger artifact; keep every result
  `mixed_or_early` and automatically approve zero root shocks;
- **DONE:** preserve all extracted signals while separately flagging repeated same-company
  evidence and speculative risk-factor language before root-shock research prioritization;
- **DONE:** build provider-free, bounded candidate research packets that preserve direct SEC
  provenance, maximize issuer/signal-family diversity, and keep every approval field fail-closed;
- **DONE:** validate completed research results against packet identity, causal evidence taxonomy,
  non-issuer corroboration, economic-node IDs, and strict cutoff before append eligibility;
- **DONE:** produce the first eligible provider-free result for the fabricated-structural-metal
  packet using two issuer backlog signals plus dated DOE, EIA, and NERC corroboration;
- **IN PROGRESS:** use the bounded root-shock research queue to obtain concrete mechanisms,
  economic-node assignments, a second independent evidence class, and external corroboration.

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
- **DONE:** record a provider-free, pre-trigger `large-power-transformers` snapshot using DOE
  physical, lead-time, qualification, and factory-expansion evidence plus an independent supplier
  capacity response;
- **IN PROGRESS:** supply observations for additional economically meaningful nodes;
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
- **DONE:** feed promoted convergence nodes into the existing pre-news node assessment without
  inventing economic-capture, reinvestment, triangulation, expectation-gap, or bottleneck scores;
- **DONE:** add a reproducible adjudicate-then-append workflow for the first real approved root
  while preserving zero upstream automatic approvals and append-only revision history;
- **DONE:** approve the first provider-free causal edge from AI data-center load growth to
  large-load grid-interconnection capacity using three dated evidence classes;
- **DONE:** approve the next bounded edge from grid-interconnection capacity to large power
  transformers and combine it with the pre-trigger transformer state without inventing a second root;
- **DONE:** reproduce one fail-closed grid node and one `pre_shock_bottleneck` transformer node
  under exact validation profiles;
- **DONE:** adjudicate an evidence-disjoint grid-modernization/resilience root and its direct
  transformer edge without reusing the AI root evidence;
- **DONE:** reproduce three production branches and promote the transformer structural assessment
  to 75.07 `priority_convergence`, while retaining the fail-closed grid-interconnection assessment;
- **DONE:** reject renamed roots or reused root evidence before independent-root breadth is counted.

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

Implementation:

- **DONE:** separate `ibs-pre-news-replay` from the frozen transcript validation CLI family;
- **DONE:** fingerprint the replay input plus root, graph, and state registries;
- **DONE:** require exact trigger-root/market-trigger identity and one frozen `as_of`;
- **DONE:** reject later evidence and explicitly held-out confirmation IDs;
- **DONE:** require explicit research judgments for every promoted node and reject injections for
  non-promoted nodes;
- **DONE:** populate and run the first real early-AI electrical-infrastructure replay package
  from exact market, root, graph, and state run IDs;
- **DONE:** preserve `large-power-transformers` at 73.0 `evidence_backed` rather than promote it
  to `pre_news_candidate`, because the frozen evidence supports the bottleneck and runway but not
  durable economic capture or a direct priced-in expectation gap;
- **DONE:** reject post-cutoff evidence, fingerprint all five inputs, and keep company mapping and
  automatic pre-news-candidate promotion disabled in production provenance;
- **DONE:** make a reader-facing Korean industry analysis a mandatory production output rather
  than treating the numerical ranking as the product; require industry structure, demand,
  value-chain transmission, bottleneck mechanics, supply response, economic capture,
  expectations, falsifiers, monitoring, scenario, and plain-language score sections;
- **DONE:** bind every factual or inferential report claim to evidence IDs already admitted by the
  exact replay, and reject unknown evidence, cutoff leakage, freeze mismatch, or missing sections;
- **DONE:** make selection provenance the first reader-facing section: exact originating market
  bucket, observed metrics versus frozen thresholds, outcome-blind persistence, issuer wording,
  and an explicit boundary between the market anomaly and downstream bottleneck inference;
- **DONE:** add the independently adjudicated grid-modernization/resilience demand root and rerun
  the exact production replay with 17 cutoff-safe records across eight evidence classes;
- **DONE:** require the Korean reader-facing report to explain both independent demand paths and
  display the structural convergence stage/score separately from the 73.0 node ranking;
- **IN PROGRESS:** define and freeze explicit later-confirmation holdouts before using the replay
  to authorize company exposure mapping.

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
