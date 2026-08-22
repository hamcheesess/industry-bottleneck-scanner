# Implementation status

This is a concise checkpoint for the current repository head. It is not a second roadmap.
[`current_roadmap.md`](current_roadmap.md) remains the only canonical roadmap and wins if
this checkpoint becomes stale.

Status vocabulary: **DONE**, **PARTIAL**, **LEGACY**, **NOT STARTED**, **BLOCKED**.

| Product layer | Status | Executable boundary | Current gap |
|---|---:|---|---|
| Architecture consolidation | **DONE** | canonical roadmap, architecture and compatibility regression rules | none |
| Broad-US identity snapshot | **PARTIAL** | dated `UniverseSnapshot`; Massive active-common-stock adapter; CIK/FIGI identity; batch checkpoint | first production enrichment run is in progress; refresh cadence remains future work |
| Market classification snapshot | **PARTIAL** | SEC-SIC division/bucket mapping and explicit unclassified denominator | measure provider SIC gaps in the first production run |
| Real EOD normalization | **DONE** | Massive adjusted grouped-daily adapter, validated raw date cache, normalized `DailyBar` history | execute 2024-11-01 through 2026-08-21 after universe enrichment completes |
| Market trigger generation | **PARTIAL** | versioned dated trigger artifact, coverage diagnostics, `ibs-market-trigger` | production broad-US run and threshold calibration |
| Market trigger replay | **DONE** | self-contained normalized archive and strict-as-of `ibs-market-trigger-replay` | real historical cases not yet calibrated |
| Source-agnostic operating evidence | **PARTIAL** | generic disclosure normalization/scanning, freshness/coverage, `operating-support-v1`, SEC submissions/archive adapter and CLIs | trigger-scoped live SEC run; automated non-SEC IR/presentation discovery |
| Frozen transcript validation v1 | **LEGACY** | preserved audit/regression CLIs and artifacts | frozen; no product extension allowed |
| Quartr transcript v2 | **LEGACY** | parked adapter/fallback/provenance experiments | `superseded_historical_only`; never a product gate |
| Persistent industry state core | **PARTIAL** | append-only snapshots, strict `latest_before`, explicit issuer-to-node mapping, AtomicSignal/external observation updater, evidence/source diversity gate | production node assignments and physical-data observations; replay-based decay policy later |
| Causal graph core | **PARTIAL** | evidence approval history and bounded traversal | root-shock/path orchestration and production edge evidence |
| Demand convergence core | **PARTIAL** | independent-root deduplication and pre-shock constraint join | persisted real graph/state integration |
| Pre-news ranking core | **PARTIAL** | six dimensions and hard gates | real-data scoring calibration |
| Company exposure mapping | **NOT STARTED** | architecture boundary only | evidence-backed node-to-company contract and mapper |
| Repo A thesis manifest | **NOT STARTED** | conceptual Repo A/Repo B boundary only | freeze only after node-level historical replay succeeds |
| Production cadence | **NOT STARTED** | none | begin only after replay and handoff stability |

The user approved `broad_us_common_stocks_v1`, supplied the Massive repository secret, and
accepted `2024-11-01` as the earliest MVP research date. The current Phase-1 execution gate
is the checkpointed production universe enrichment followed by the adjusted-history
backfill. Phase 2 must not redefine Phase 1 outputs or bypass calibration.
