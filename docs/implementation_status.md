# Implementation status

This is a concise checkpoint for the current repository head. It is not a second roadmap.
[`current_roadmap.md`](current_roadmap.md) remains the only canonical roadmap and wins if
this checkpoint becomes stale.

Status vocabulary: **DONE**, **PARTIAL**, **LEGACY**, **NOT STARTED**, **BLOCKED**.

| Product layer | Status | Executable boundary | Current gap |
|---|---:|---|---|
| Architecture consolidation | **DONE** | canonical roadmap, architecture and compatibility regression rules | none |
| Broad-US identity snapshot | **DONE** | dated `UniverseSnapshot`, issuer/security IDs and explicit unresolved identities | production membership refresh policy remains future cadence work |
| Market classification snapshot | **DONE** | dated `MarketUniverseSnapshot`, bottom-up sector/bucket membership and explicit unclassified denominator | production classification snapshot still needs to be supplied |
| Real EOD normalization | **DONE** | Massive adjusted grouped-daily adapter, validated raw date cache, normalized `DailyBar` history | live backfill requires provider credentials and entitlement verification |
| Market trigger generation | **PARTIAL** | versioned dated trigger artifact, coverage diagnostics, `ibs-market-trigger` | production broad-US run and threshold calibration |
| Market trigger replay | **DONE** | self-contained normalized archive and strict-as-of `ibs-market-trigger-replay` | real historical cases not yet calibrated |
| Source-agnostic operating evidence | **NOT STARTED** | existing `SourceDocument` / scanner / `AtomicSignal` are reusable | release / 8-K / 10-Q / presentation adapters and `OperatingSupport` |
| Frozen transcript validation v1 | **LEGACY** | preserved audit/regression CLIs and artifacts | frozen; no product extension allowed |
| Quartr transcript v2 | **LEGACY** | parked adapter/fallback/provenance experiments | `superseded_historical_only`; never a product gate |
| Persistent industry state core | **PARTIAL** | append-only snapshots and strict `latest_before` lookup | automatic evidence-to-state updater |
| Causal graph core | **PARTIAL** | evidence approval history and bounded traversal | root-shock/path orchestration and production edge evidence |
| Demand convergence core | **PARTIAL** | independent-root deduplication and pre-shock constraint join | persisted real graph/state integration |
| Pre-news ranking core | **PARTIAL** | six dimensions and hard gates | real-data scoring calibration |
| Company exposure mapping | **NOT STARTED** | architecture boundary only | evidence-backed node-to-company contract and mapper |
| Repo A thesis manifest | **NOT STARTED** | conceptual Repo A/Repo B boundary only | freeze only after node-level historical replay succeeds |
| Production cadence | **NOT STARTED** | none | begin only after replay and handoff stability |

The immediate blocker to closing Phase 1 is not a code dependency: it is a real dated
broad-US membership/classification input plus Massive API credentials for the initial
adjusted-history backfill. Phase 2 must not redefine Phase 1 outputs or bypass that
calibration requirement.
