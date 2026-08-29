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
| Causal diagnosis | **PARTIAL** | 28 provider-free dated diagnoses, bounded strict-as-of research packets, non-appending adjudication, and one eligible AI data-center electric-load result using three evidence classes | research and adjudicate the remaining economically coherent candidates |
| Frozen transcript validation v1 | **LEGACY** | preserved audit/regression CLIs and artifacts | frozen; no product extension allowed |
| Quartr transcript v2 | **LEGACY** | parked adapter/fallback/provenance experiments | `superseded_historical_only`; never a product gate |
| Persistent industry state core | **PARTIAL** | append-only snapshots, strict `latest_before`, source-diverse grid-interconnection snapshot, severely constrained pre-trigger large-power-transformer snapshot, explicit issuer-to-node mapping, AtomicSignal/external observation updater | additional node observations and replay-based decay policy later |
| Causal graph core | **PARTIAL** | evidence approval history, bounded traversal, reproducible append-only workflows for the first real root and its two-edge grid-interconnection-to-transformer path, versioned orchestration | independent demand-root and additional value-chain edges |
| Demand convergence core | **PARTIAL** | first real production graph/state integration, one fail-closed grid assessment, one `pre_shock_bottleneck` transformer assessment, independent-root deduplication, strict pre-shock join | independent-root convergence and replay calibration |
| Pre-news ranking core | **PARTIAL** | six dimensions and hard gates plus the first production large-power-transformer score: 73.0 `evidence_backed` | validate economic capture and expectation gap without promoting from supply constraints alone |
| Historical pre-news replay | **PARTIAL** | first production replay completed from four exact upstream runs; one transformer node, 14 evidence records, eight evidence classes, strict cutoff, fingerprinted freeze and provenance | add an independent demand root and later-confirmation holdouts before any company mapping |
| Reader-facing industry analysis | **PARTIAL** | mandatory Korean narrative schema/CLI; exact replay/freeze join; evidence-bound facts and inferences; industry structure, demand, value-chain, bottleneck, economics, scenarios, falsifiers and monitoring; first transformer report | repeat the same narrative gate for every later promoted economic node |
| Company exposure mapping | **NOT STARTED** | architecture boundary only | evidence-backed node-to-company contract and mapper |
| Repo A thesis manifest | **NOT STARTED** | conceptual Repo A/Repo B boundary only | freeze only after node-level historical replay succeeds |
| Production cadence | **NOT STARTED** | none | begin only after replay and handoff stability |

The user approved `broad_us_common_stocks_v1`, supplied the Massive repository secret, and
accepted `2024-11-01` as the earliest MVP research date. Market replay and the trigger-scoped
SEC pass are complete. The first external causal result is eligible for append from the exact
`2026-08-21` packet. Its bounded path now reaches `large-power-transformers` through two
evidence-backed edges, and a source-diverse pre-trigger transformer snapshot is severely
constrained without using later outcomes. The first production historical replay preserved that
node at `evidence_backed`, not `pre_news_candidate`, because economic capture and expectation gap
remain weakly evidenced. Its score is now accompanied by a required Korean industry report that
explains the physical mechanism, limitations, scenarios and falsifiers using only the 14 replay
evidence records. The current execution gate is independent-root evidence and explicit
later-confirmation holdouts. This work must
not redefine Phase-1 outputs, change frozen thresholds, or
approve a root shock without independent evidence and strict-as-of provenance.
