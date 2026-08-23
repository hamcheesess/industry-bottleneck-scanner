# Implementation compatibility map

This document prevents the architecture pivot from turning into a rewrite. It defines which existing modules remain authoritative, which are reusable subsystems, which are active new modules, and which are parked historical experiments.

## Status vocabulary

- **KEEP** — authoritative contract or correctness invariant; new code should reuse it.
- **REUSE** — useful subsystem; callable from the new architecture but no longer the top-level control flow.
- **ACTIVE** — current architecture module being developed.
- **PARKED** — code may remain for audit/future optional use, but active execution must not depend on it.
- **FROZEN** — historical validation artifact; do not tune or retrofit.
- **DOWNSTREAM** — belongs to Repo B and must not be imported into Repo A.

## Current module map

| Area | Module / artifact | Status | Current role |
|---|---|---:|---|
| Core evidence | `models.py` | KEEP | `SourceDocument`, `AtomicSignal`, classification/provenance contracts |
| Scanner | `scanner.py`, `vocabulary.py`, `candidate_*`, `discovery_pipeline.py` | KEEP | deterministic operating-language extraction and correctness invariants |
| Transcript normalization | `transcript_pipeline.py`, `transcript_store.py`, `alpha_vantage.py` | REUSE | optional operating-evidence source and normalized cache |
| Transcript comparable scan | `batch_orchestration.py`, `experiment.py`, `aggregation.py` | REUSE | like-for-like operating acceleration where comparable windows exist |
| Frozen v1 validation | `validation_*`, frozen manifests/policy | FROZEN | audit trail and regression source; not the active discovery gate |
| Quartr adapter | `quartr.py` | PARKED | synthetic-tested optional adapter; unusable API access means no active dependency |
| Transcript fallback resolver | `transcript_fallback.py` | PARKED | generic pair-coherent transcript fallback idea; not current system control flow |
| Quartr-era v2 provenance | `v2_source_provenance.py` | PARKED | historical transcript-provider provenance utility; do not extend as the new source model |
| Market history | `market_history.py` | ACTIVE | provider-independent EOD feature calculation with `as_of` safety |
| Market universe provider | `massive_universe.py`, `massive_universe_cli.py` | ACTIVE | dated `broad_us_common_stocks_v1` membership, CIK/FIGI identity, SEC-SIC classification, free-plan checkpoints |
| Market universe join | `market_universe.py` | ACTIVE | dated canonical identity plus sector/bucket membership and explicit classification gaps |
| Market trigger | `market_trigger.py` | ACTIVE | bottom-up industry/economic-bucket market breadth trigger |
| EOD normalization | `eod_market_data.py` | ACTIVE | Massive grouped-daily provider boundary, raw date cache, normalized `DailyBar` histories and explicit coverage |
| Market artifacts / CLI | `market_trigger_artifacts.py`, `market_trigger_cli.py`, `market_trigger_replay_cli.py` | ACTIVE | self-contained normalized history, dated v1 triggers, live collection and strict-as-of replay outside legacy validation |
| Disclosure normalization | `disclosure_documents.py`, `source_scan.py`, `operating_evidence_cli.py` | ACTIVE | provider-neutral public disclosures -> existing `SourceDocument` / scanner / `AtomicSignal` contracts |
| SEC disclosure provider | `sec_edgar.py`, `sec_edgar_cli.py` | ACTIVE | cache-first, strict-as-of 8-K/10-Q/10-K and EX-99 collection below normalization |
| Operating support | `operating_support.py` | ACTIVE | freshness/coverage-aware one-sided evidence plus optional comparable acceleration |
| Causal diagnosis | `causal_diagnosis.py` | ACTIVE | joins market trigger with provider-independent `OperatingSupport`; legacy acceleration input remains compatible |
| Causal node ranking | `causal_expansion.py` | ACTIVE | pre-news research-priority dimensions and hard gates |
| Causal graph | `causal_graph.py` | ACTIVE | append-only approved economic dependency edges and bounded traversal |
| Root shock / path orchestration | `root_demand_shock.py`, `causal_orchestration.py` | ACTIVE | append-only shock approval, as-of graph composition, `DemandBranch` and convergence artifacts |
| Industry state | `industry_state.py` | ACTIVE | append-only pre-shock supply-state memory |
| Industry-state updater | `industry_state_updater.py`, `industry_state_update_cli.py` | ACTIVE | explicit economic-node assignments, deterministic AtomicSignal mapping, external observations, evidence/source-diversity gate |
| Demand convergence | `demand_convergence.py` | ACTIVE | new-shock x pre-shock constraint x independent-root convergence |
| Historical pre-news replay | `pre_news_replay.py`, `pre_news_replay_cli.py` | ACTIVE | fail-closed promoted-node join, frozen input fingerprints, holdout gate, existing node ranker orchestration |
| Repo B | `investment-research-automation` | DOWNSTREAM | financial gate, deep research, DCF, final report |

## Compatibility rules

### 1. `AtomicSignal` remains the bridge from old scanner to new architecture

Do not invent a second parallel operating-signal schema merely because the top-level roadmap changed. New public-document adapters should normalize into `SourceDocument`, then reuse the existing scanner to produce `AtomicSignal`.

If a new evidence type cannot be represented as an `AtomicSignal` because it is structural/physical rather than issuer operating language, represent it as `CausalEvidence` instead. Do not force physical data into the scanner taxonomy.

### 2. Separate three evidence roles

The system now has three related but distinct evidence contracts:

- `AtomicSignal` — extracted issuer operating phenomenon;
- `CausalEvidence` — source-backed evidence supporting a graph edge or node assessment;
- `IndustryStateSnapshot` — time-stamped aggregate state of an economic value-chain node.

These should reference each other through provenance IDs rather than duplicating raw text into several schemas when persistence is implemented.

### 3. Old current-vs-baseline acceleration is optional, not deleted

Comparable-window acceleration remains valuable when both windows are available and source-comparable. It is especially useful for earnings-call/release operating acceleration.

However, the active discovery path must not require complete transcript pairs for every issuer. Future causal diagnosis should accept a broader provider-independent `OperatingSupport` interface that can combine:

- old `AccelerationSnapshot` when available;
- recent one-sided operating evidence;
- since-last-earnings public updates;
- source coverage/freshness diagnostics.

`OperatingSupport` should wrap/reference these outputs. It must not replace `AtomicSignal`, duplicate the scanner taxonomy, or mutate `AccelerationSnapshot` merely to satisfy the new architecture.

That adapter is now implemented in `operating_support.py`. `causal_diagnosis.py` accepts it
without importing any provider, while retaining the prior `AccelerationSnapshot` call shape for
existing consumers.

### 4. Provider code stays below evidence normalization

Market/filing/transcript providers must not leak into causal ranking or convergence logic.

Forbidden architectural direction:

```text
causal_graph -> Quartr / Alpha Vantage / price provider
industry_state -> transcript provider
pre_news ranking -> SEC transport
```

Required direction:

```text
provider adapter
  -> normalized source/evidence artifact
  -> scanner / state updater / graph evidence
  -> causal logic
```

A future EOD vendor or SEC client may be replaced without changing `market_trigger`, `causal_graph`, `industry_state`, `demand_convergence`, or pre-news scoring contracts.

### 5. Quartr-era code is parked, not deleted

The Quartr adapter and transcript fallback resolver were technically valid experiments and may be useful if access changes later. Deleting them would lose tested work; making the current architecture depend on them would recreate the coverage bottleneck.

Therefore:

- keep their tests;
- do not add new active imports from market/causal/state modules into Quartr/fallback modules;
- do not make Quartr availability a validation gate;
- do not modify frozen v1 to use them;
- do not extend `v2_source_provenance.py` into the general evidence-provenance model.

### 6. Economic node identity must not equal ticker identity

`IndustryStateSnapshot.node_id`, causal graph nodes, and convergence targets represent economic value-chain nodes such as `large-power-transformers` or `data-center-switchgear`, not one listed company.

Company mapping happens later. This keeps many-to-many value-chain structure possible and prevents company classifications from becoming the causal graph itself.

### 7. Industry classifications and economic nodes have different jobs

- sector / industry / subindustry: broad bottom-up market aggregation and operating breadth;
- dynamic economic subcluster: more specific market grouping when justified;
- causal/value-chain node: physical/economic dependency graph after diagnosis.

Do not silently replace GICS-like grouping with hand-written causal nodes in the Market Trigger layer. Do not force value-chain analysis to remain inside static industry labels after a trigger is diagnosed.

### 8. Append-only history is a system invariant

Causal graph approvals and industry-state snapshots should preserve history. Historical replay must retrieve what was known at an earlier `as_of`, not reconstruct the past from today's latest state.

Future root-demand-shock, expectation-gap, convergence, and company-exposure artifacts should follow the same rule when historical validation begins.

Root-demand-shock, branch, and convergence artifacts now follow this append-only/as-of rule.
Replay node judgments and outputs now preserve an exact `as_of`, input fingerprints, and explicit
held-out evidence IDs. Company-exposure artifacts remain future work.

### 9. Repo B remains isolated

Repo A must not import Repo B valuation/financial-risk logic. Repo B must not become a discovery dependency. The only future coupling is a small versioned thesis manifest.

### 10. One orchestration layer, no new monolith

Do not turn `batch_cli.py`, a frozen `validation_*` CLI, or any provider adapter into the new top-level application.

The future market-triggered workflow should have a new orchestration entry point that composes stable contracts in this order:

```text
market artifacts
  + normalized operating support
  -> diagnosis / root shock
  -> approved graph paths
  + pre-shock state
  -> convergence
  -> node ranking
  -> company exposure
```

The orchestration layer may depend on the domain modules. Domain modules must not depend back on orchestration.

### 11. New validation must not mutate the frozen validation namespace

The large existing `validation_*` family belongs to transcript Phase-1/frozen-v1 history. Reusing its lessons and low-level helpers is fine, but new end-to-end market-triggered replay should get a separate entry point/module family.

This prevents an old transcript validation state machine from becoming an accidental dependency of the new product architecture.

### 12. Do not physically reorganize working modules yet

The conceptual architecture may eventually justify `sources/`, `market/`, `causal/`, `state/`, or `validation/` packages. Do not perform that directory migration now.

First make the canonical pipeline work with compatibility adapters. A package move is justified only after interfaces are stable and can be migrated with import aliases/tests. This keeps existing CLIs, tests, and frozen fingerprints from breaking for cosmetic reasons.

## Immediate refactoring policy

Do **not** rewrite old modules just to make names match the new roadmap.

Refactor only when one of these is true:

1. an active stage needs a provider-independent interface;
2. old code creates a real dependency conflict;
3. duplicate schemas begin representing the same concept;
4. a historical replay exposes a correctness defect;
5. a stable handoff boundary is ready to freeze.

Until then, compatibility adapters are preferred over broad rewrites.

## Next allowed interface changes

In roadmap order, the next new interfaces should be limited to:

1. an EOD market-data adapter that outputs the already-defined daily-bar input contract;
2. source-agnostic disclosure adapters that output `SourceDocument`;
3. `OperatingSupport` as a thin provider-independent causal-diagnosis input;
4. root-demand-shock/path persistence contracts;
5. company exposure mapping only after the real historical node-level replay succeeds.

Anything outside this order should require an explicit architectural reason rather than being added opportunistically.
