# Phase-1 validation v2 — draft contract

Status: **draft only; architecture selected, provider access pending; not frozen, not executable, and not a replacement for frozen v1**.

Frozen v1 remains the audit trail of the Alpha-Vantage-only experiment. V2 exists to separate source coverage, extraction correctness, acceleration behavior, control precision, and blind discovery so one failure mode cannot masquerade as another.

## Why v2 is needed

Frozen v1 produced useful but mixed findings:

- six of seven cases became complete-cohort and fresh;
- the remaining blind case was blocked by provider-missing transcript coverage rather than scanner logic;
- positive stage recall on the fresh labeled subset was 2/3;
- expected-metric recall was 6/7;
- one of three completed controls triggered;
- one positive label required an exact taxonomy metric that was narrower than the external phenomenon evidence;
- one positive current/baseline window compared against a baseline that was already accelerating.

V2 must not attempt to make those v1 outcomes pass. It must make each property independently testable.

## Five independent validation dimensions

### 1. Source coverage

Question: can the frozen cohort be represented with comparable source documents before scanner behavior is evaluated?

Rules:

- Every case freezes its issuer/window cohort before scanning.
- A case is scoreable only when every required issuer-window has a source document from the predeclared source policy.
- Missing sources never count as negative signals and never cause silent cohort shrinkage.
- Source coverage is reported separately from scanner recall/precision.
- Fallback documents must preserve the same semantic source class. A transcript fallback may replace a transcript; an earnings release or 10-Q is corroboration, not a hidden substitute for an unavailable call transcript.
- Provider identity and document provenance remain explicit in every cached normalized document.
- Fallback occurs only on an explicit provider `missing` result. A rate limit or ordinary provider error stops the chain; it does not silently change provider.
- A matched issuer's current and baseline windows must come from the same provider. If the primary source misses one side, fallback must supply the complete issuer pair. This prevents provider-format differences from manufacturing apparent acceleration.
- Different issuers inside the same frozen cohort may resolve to different providers, but provider mix must be reported as a validation diagnostic.

### Selected multi-source hierarchy

The architecture decision is now **multi-source transcript fallback**.

Draft provider order:

1. `alpha_vantage` — primary transcript source.
2. `quartr_edited` — fallback using Quartr edited transcript type ID 22 only.

Quartr raw transcript type ID 15 is not an allowed substitute. The edited transcript dataset adds `speaker_mapping` with speaker name, role, and company affiliation; that metadata is important because Phase 1 already found that analyst questions must not be treated as issuer operating evidence. Quartr also documents transcript availability for 95% of events within 45 minutes after conclusion and exposes historical transcripts through its REST API.

Official references reviewed for this decision:

- Quartr transcript structure and speaker mapping: https://quartr.com/docs/datasets/earnings-call-transcripts
- Quartr data availability/SLA: https://quartr.com/docs/data-overview
- Quartr API pricing/access: https://quartr.com/pricing/overview
- Financial Modeling Prep transcript endpoint and pricing: https://intelligence.financialmodelingprep.com/developer/docs and https://site.financialmodelingprep.com/pricing-plans
- Finnhub transcript schema/pricing: https://finnhub.io/docs/api/indices-constituents and https://finnhub.io/pricing

Financial Modeling Prep is not selected for the frozen fallback slot at this stage even though it has a self-service transcript endpoint and an Ultimate tier with earnings call transcripts. Its public transcript documentation does not expose the same explicit speaker-role/company mapping contract that the current analyst-exclusion provenance rule needs.

Finnhub remains a technically viable contingency because its premium transcript response documents participant roles and call session, but transcript access is an add-on/contact-sales product. It is not part of the selected hierarchy while Quartr remains the preferred structured fallback.

**Access is not yet approved or purchased.** Quartr API pricing is contact-sales. The repository can implement and test the adapter against synthetic payloads now, but v2 cannot be frozen or executed with Quartr until access terms are accepted and a key is available.

### 2. Phenomenon / extraction recall

Question: when source-backed operating evidence is present, can the scanner extract the intended broad phenomenon without requiring a more specific taxonomy label than the source supports?

Rules:

- Ground truth is sentence- or passage-backed and source-cited.
- Expected labels are broad scanner concepts or explicitly source-supported metrics.
- A case cannot require a narrow metric solely because it would be convenient for the current vocabulary.
- Extraction recall is evaluated on current-window evidence only; it does not require acceleration.
- Evidence from analyst questions is ineligible. Management prepared remarks and management Q&A answers remain eligible.
- Direction, negation, resolution, speaker role, and source section are part of correctness.

Recommended draft gate: at least **5 of 6** frozen extraction cases recovered, with no unresolved provenance/correctness defect.

### 3. True window-to-window acceleration recall

Question: does the aggregation/acceleration layer identify a real increase from a quieter baseline to a stronger current window?

Rules:

- Baseline and current windows are chosen from an external event timeline before scanner outcomes are inspected.
- The external timeline must support that baseline is materially quieter than current; a baseline already documented as accelerating is not a valid acceleration-positive pair.
- Comparable issuer cohorts are frozen before scanning.
- Acceleration recovery is judged by stage (`watchlisted` or stronger) plus predeclared broad core-category behavior, not by every exact taxonomy metric from the extraction test.
- Raw mention-count growth alone is insufficient.

Recommended draft gate: at least **4 of 6** frozen acceleration-positive pairs reach watchlisted-or-stronger, and at least **3 of 6** reach triggered-or-confirmed.

### 4. Control precision

Question: how often does the system trigger in matched quiet/pre-event windows?

Rules:

- Controls are selected from the same issuer families / sectors as positives where practical.
- Each control has external evidence that the tested window precedes the target phenomenon or is otherwise a plausibly quiet comparator.
- Controls are complete-cohort and source-complete before scoring.
- A triggered control is never tuned away case-by-case. It receives issuer-evidence audit and one of three post-run classifications: scanner correctness defect, ambiguous/precursor real signal, or control-label weakness.
- Only general correctness defects reproducible independently of the case may change production extraction code during a frozen run.

Recommended draft size/gate: **8 controls**, with at most **1 triggered/confirmed false positive** after evidence review. This is a development gate, not a statistical significance claim.

### 5. Blind discovery / ranking

Question: can an outcome-blind broad-US proxy cohort surface nontrivial clusters without a handpicked positive theme?

Rules:

- Cohort selection is deterministic and outcome-blind.
- Cohort, source policy, windows, aggregation level, and ranking contract are frozen before scanning.
- No issuer is removed or replaced after scanner output is visible.
- Blind output is judged first as discovery/ranking quality, not as a binary known-positive recall case.
- Post-scan external validation may classify surfaced clusters as supported, unsupported, or indeterminate, but must not rewrite scanner inputs.
- Absence of a trigger is a valid blind result and must be retained.

Draft success condition: at least one surfaced watchlisted-or-stronger cluster in the frozen blind cohort receives independent post-scan support **or** the blind run produces a well-calibrated no-trigger result with no unsupported high-ranked cluster. The exact ranking metric and review rubric must be frozen before execution.

## Proposed v2 case structure

The draft target is intentionally modest enough for cache-first browser/Codespaces validation while large enough to avoid the v1 denominator problems:

- 6 extraction cases,
- 6 acceleration-positive pairs,
- 8 matched controls,
- 1 outcome-blind cohort with multiple independently triggerable groups,
- explicit source-coverage accounting across every issuer-window.

Extraction and acceleration cases may share underlying issuers/documents, but their labels and success criteria are separate.

## Gate arithmetic must use integer counts

V2 must not repeat the v1 `0.67` ambiguity. Frozen gates should be expressed as numerator/denominator counts first and percentages only as display values.

Examples:

- extraction recall: `>= 5/6`,
- acceleration watch-or-trigger: `>= 4/6`,
- acceleration trigger-or-confirm: `>= 3/6`,
- controls: `<= 1/8` triggered/confirmed false positives.

## Calibration freeze

Once v2 is frozen:

- no vocabulary changes merely to recover a labeled case;
- no semantic threshold changes merely to reduce a control trigger;
- no aggregation or trigger threshold changes merely to improve the gate;
- no cohort/window/source substitutions after outcomes are visible;
- only general correctness invariants, reproduced with synthetic or outcome-independent regression tests, may change production code during the frozen round;
- any such correctness change invalidates stale result fingerprints and requires one same-version rerun of the full v2 set.

## Implementation boundary before v2 freeze

The repository now contains a provider-agnostic fallback resolver and a Quartr edited-transcript adapter, but they are intentionally not wired into frozen-v1 collection or scanner execution.

Before v2 can become executable:

1. Quartr access terms/key must be available or the fallback provider must be changed before freeze.
2. The v2 collector must use the ordered resolver with per-provider bounded budgets.
3. Provider mix and issuer-pair provider coherence must enter input fingerprints and validation artifacts.
4. Exact v2 extraction cases, acceleration windows, controls, and blind ranking rubric must be frozen.
5. The full v2 source policy and case manifest must be reviewed once before any v2 scanner outcome is inspected.

## Phase-2 gate after v2

V2 validation is a discovery-engine gate, not an investment-performance claim. Phase 2 may begin only if:

- source coverage is sufficient under the frozen v2 source policy,
- no unresolved scanner correctness defect remains,
- extraction recall meets its frozen gate,
- acceleration recall meets its frozen gate,
- control precision meets its frozen gate after evidence review,
- the blind discovery/ranking review is completed,
- the whole v2 result is reviewed without post-hoc threshold or cohort changes.

Repo B remains untouched until Repo A has passed the appropriate discovery gate and Phase-2 bottleneck/economic-capture work later produces a candidate handoff contract.
