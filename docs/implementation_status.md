# Implementation status

This is a concise checkpoint for the current repository head. It is not a second roadmap.
[`current_roadmap.md`](current_roadmap.md) remains the only canonical roadmap and wins if
this checkpoint becomes stale.

Status vocabulary: **DONE**, **PARTIAL**, **LEGACY**, **NOT STARTED**, **BLOCKED**.

| Product layer | Status | Executable boundary | Current gap |
|---|---:|---|---|
| Architecture consolidation | **DONE** | canonical roadmap, architecture and compatibility regression rules | none |
| Broad-US identity snapshot | **PARTIAL** | production `2026-08-21` snapshot plus historical `2025-05-30` snapshot completed; dated `UniverseSnapshot`; CIK/FIGI identity; batch checkpoint; terminal overview-gap diagnostics | refresh cadence |
| Market classification snapshot | **PARTIAL** | historical snapshot has 4,241/5,054 members classified by SEC SIC with an explicit 813-member gap denominator | later classification enrichment policy |
| Real EOD normalization | **DONE** | 1,740,696 normalized bars from 2024-11-01 through 2026-08-21; 4,071 tickers satisfy the 127-session minimum; no future bars | retain dated artifact and add historical-universe archive |
| Market trigger generation | **PARTIAL** | historical archive has 382 bucket assessments and 50 raw triggers at 2026-08-21; versioned artifact, coverage diagnostics, `ibs-market-trigger` | blind trigger-quality assessment before promotion to causal research |
| Market trigger replay | **DONE** | self-contained normalized archive, separate historical universe/market cutoffs, strict-as-of replay, and provider-free 16-date monthly calibration series | outcome-held-out trigger review |
| Source-agnostic operating evidence | **PARTIAL** | generic disclosure normalization/scanning, freshness/coverage, `operating-support-v1`, SEC submissions/archive adapter and CLIs | trigger-scoped live SEC run; automated non-SEC IR/presentation discovery |
| Frozen transcript validation v1 | **LEGACY** | preserved audit/regression CLIs and artifacts | frozen; no product extension allowed |
| Quartr transcript v2 | **LEGACY** | parked adapter/fallback/provenance experiments | `superseded_historical_only`; never a product gate |
| Persistent industry state core | **PARTIAL** | append-only snapshots, strict `latest_before`, explicit issuer-to-node mapping, AtomicSignal/external observation updater, evidence/source diversity gate | production node assignments and physical-data observations; replay-based decay policy later |
| Causal graph core | **PARTIAL** | evidence approval history, bounded traversal, append-only root-shock approvals, versioned path orchestration | production root/edge evidence |
| Demand convergence core | **PARTIAL** | approved roots/edges -> `DemandBranch`, independent-root deduplication, strict pre-shock state join, persisted assessments | real graph/state integration and replay calibration |
| Pre-news ranking core | **PARTIAL** | six dimensions and hard gates | real-data scoring calibration |
| Historical pre-news replay | **PARTIAL** | promoted-convergence join, exact frozen `as_of`, input fingerprints, held-out evidence gate, `ibs-pre-news-replay` | first real early-AI electrical-infrastructure replay package |
| Company exposure mapping | **NOT STARTED** | architecture boundary only | evidence-backed node-to-company contract and mapper |
| Repo A thesis manifest | **NOT STARTED** | conceptual Repo A/Repo B boundary only | freeze only after node-level historical replay succeeds |
| Production cadence | **NOT STARTED** | none | begin only after replay and handoff stability |

The user approved `broad_us_common_stocks_v1`, supplied the Massive repository secret, and
accepted `2024-11-01` as the earliest MVP research date. The current Phase-1 execution gate
is the checkpointed production universe enrichment followed by the adjusted-history
backfill. Phase 2 must not redefine Phase 1 outputs or bypass calibration.
