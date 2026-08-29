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
| Causal diagnosis | **PARTIAL** | 28 provider-free dated diagnoses, bounded strict-as-of research packets, non-appending adjudication, and two evidence-disjoint eligible demand roots: AI data-center electric load plus grid modernization/resilience | research and adjudicate the remaining economically coherent candidates |
| Frozen transcript validation v1 | **LEGACY** | preserved audit/regression CLIs and artifacts | frozen; no product extension allowed |
| Quartr transcript v2 | **LEGACY** | parked adapter/fallback/provenance experiments | `superseded_historical_only`; never a product gate |
| Persistent industry state core | **PARTIAL** | append-only snapshots, strict `latest_before`, source-diverse grid-interconnection snapshot, severely constrained pre-trigger large-power-transformer snapshot, explicit issuer-to-node mapping, AtomicSignal/external observation updater | additional node observations and replay-based decay policy later |
| Causal graph core | **PARTIAL** | evidence approval history, bounded traversal, reproducible append-only workflows for two independent roots and three paths/edges reaching the transformer bottleneck, versioned orchestration | additional value-chain edges only where independently evidenced |
| Demand convergence core | **PARTIAL** | production two-root integration: three branches, fail-closed grid assessment, transformer 75.07 `priority_convergence`, strict pre-shock join, renamed-root and evidence-reuse rejection | later-confirmation calibration and additional historical cases |
| Pre-news ranking core | **PARTIAL** | six dimensions and hard gates plus the first production large-power-transformer score: 73.0 `evidence_backed` | validate economic capture and expectation gap without promoting from supply constraints alone |
| Historical pre-news replay | **PARTIAL** | two-root production replay completed from exact upstream runs; one transformer node, 17 evidence records across eight classes, strict cutoff, fingerprinted freeze/provenance, 73.0 `evidence_backed` ranking | freeze the committed later-confirmation plan in a production artifact |
| Later-confirmation holdout | **PARTIAL** | fail-closed plan/evidence/diagnostic schemas; four dated industrial validation windows; minimum source/entity diversity; Korean reader explanation; automatic reranking disabled; unfrozen security expectation gap blocked | run the initial production freeze, then append only evidence observed inside each window |
| Reader-facing industry analysis | **PARTIAL** | mandatory Korean narrative schema/CLI; exact replay/freeze join; evidence-bound facts and inferences; industry structure, demand, value-chain, bottleneck, economics, scenarios, falsifiers and monitoring; first transformer report | repeat the same narrative gate for every later promoted economic node |
| Company exposure mapping | **NOT STARTED** | architecture boundary only | evidence-backed node-to-company contract and mapper |
| Repo A thesis manifest | **NOT STARTED** | conceptual Repo A/Repo B boundary only | freeze only after node-level historical replay succeeds |
| Production cadence | **NOT STARTED** | none | begin only after replay and handoff stability |

The user approved `broad_us_common_stocks_v1`, supplied the Massive repository secret, and
accepted `2024-11-01` as the earliest MVP research date. Market replay and the trigger-scoped
SEC pass are complete. The first external causal result is eligible for append from the exact
`2026-08-21` packet. Two evidence-disjoint demand roots now reach `large-power-transformers`:
AI data-center electric-load growth through grid interconnection, and grid-modernization/resilience
investment directly through transmission and substation projects. The production convergence has
three branches and ranks the severely constrained transformer node at 75.07 `priority_convergence`.
The replay still preserves the node at 73.0 `evidence_backed`, not `pre_news_candidate`, because
economic capture and expectation gap remain weakly evidenced. Its required Korean industry report
explains all 17 replay evidence records, both demand mechanisms, limitations, scenarios and
falsifiers. The committed later-confirmation plan predeclares 90/180/365-day industrial tests and
keeps the missing pre-cutoff security expectation snapshot blocked. The current execution gate is
the initial production holdout freeze. This work must
not redefine Phase-1 outputs, change frozen thresholds, or
approve a root shock without independent evidence and strict-as-of provenance.
