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
| Market trigger generation | **DONE** | 382 bucket assessments, 50 latest raw triggers, outcome-blind review separating 28 persistent from 22 emerging buckets, thresholds frozen | monitor later evidence precision without retroactive tuning |
| Market trigger replay | **DONE** | self-contained normalized archive, separate historical universe/market cutoffs, strict-as-of replay, provider-free 16-date series, hashed quality artifact | none for Phase-1 boundary |
| Trigger-scoped SEC queue | **DONE** | 28 persistent buckets joined to 479 unique CIK issuers; five batches capped at 100; one duplicate share class recorded | none for the bounded production queue |
| Source-agnostic operating evidence | **PARTIAL** | 22,863 trigger-scoped SEC disclosures, 77,749 normalized documents, 7,135 signals, freshness/coverage, and `operating-support-v1` | non-SEC corroboration only where causal research requires it |
| Causal diagnosis | **PARTIAL** | 28 provider-free dated diagnoses, signal-quality audit, and bounded strict-as-of research packets with automatic approval disabled | concrete mechanisms, economic-node assignments, second evidence classes, and external corroboration |
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
accepted `2024-11-01` as the earliest MVP research date. Market replay and the trigger-scoped
SEC pass are complete. The current execution gate is external causal research over the bounded
root-shock packets. It must not redefine Phase-1 outputs, change frozen thresholds, or approve a
root shock without independent evidence and strict-as-of provenance.
