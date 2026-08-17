# Market-triggered causal discovery roadmap

## Objective

The discovery engine does not try to predict every quiet industry before the market reacts. It starts from a visible market anomaly, determines whether the move is supported by a structural operating demand shock, then expands outward through the value chain to find economically important nodes before large contracts or explosive reported earnings make the second- and third-order beneficiaries obvious.

The core question is not "what stock has not gone up yet?" It is:

> If the observed demand shock persists, which value-chain nodes must absorb the incremental demand, where is supply least elastic, who can capture the economics, and which of those implications appear least reflected in current market attention?

## High-level flow

```text
Broad US universe
    -> Market Trigger
    -> Causal Diagnosis
    -> Structural Theme or Narrative-Only
    -> Value-chain Hypothesis Graph
    -> Evidence-backed Edge Approval
    -> Pre-News Chain Selection
    -> Bottleneck / Economic Capture Ranking
    -> Listed-company Mapping
    -> Repo B Underwriting
```

The existing transcript scanner becomes one evidence source inside Causal Diagnosis and edge validation. Transcript completeness is not a discovery gate.

## 1. Market Trigger

Run cheap end-of-day or weekly calculations across the broad-US universe. Real-time data is not required.

Candidate trigger inputs:

- 1m / 3m / 6m return,
- market-relative and sector-relative return,
- cross-company breadth inside an industry/subindustry,
- abnormal volume,
- distance to 52-week high,
- optional later: estimate-revision breadth.

The output is an `IndustryMarketTrigger`, not a stock recommendation. A valid trigger should prefer broad industry participation over a single-stock spike.

## 2. Causal Diagnosis

For the triggered cluster, collect inexpensive public operating evidence:

- earnings-call transcripts when available,
- earnings releases,
- 8-K / 10-Q disclosures,
- investor presentations,
- customer and supplier disclosures.

Run the existing Capex / Demand / Scarcity / Pricing scanner. The diagnosis classifies the market trigger as one of:

- `structural_operating`: broad, source-backed operating acceleration,
- `narrative_led`: market move with weak operating support,
- `mixed_or_early`: partial support requiring more evidence,
- `unresolved`.

No value-chain expansion is promoted merely because prices rose.

## 3. Value-chain Hypothesis Graph

A structural theme creates a root demand shock. Candidate edges may be proposed mechanically, manually, or later by an LLM, but an LLM proposal is never sufficient for approval.

Allowed edge relations should stay economically explicit:

- `requires_input`,
- `requires_capacity`,
- `capacity_enabler`,
- `complement`,
- `substitute`,
- `distribution_or_service`,
- `physical_constraint`.

Each edge records:

- upstream/root node,
- downstream/affected node,
- mechanism,
- expected demand sensitivity,
- estimated time lag,
- supply elasticity,
- evidence and provenance,
- confidence.

This prevents vague chains such as `AI -> electricity -> copper -> miner` from being promoted without an explicit economic mechanism.

## 4. Evidence-backed Edge Approval

Every material edge must be supported by at least two independent evidence classes before it can become a research path. Useful evidence classes include:

- customer capex or capacity plans,
- customer architecture / bill-of-material dependence,
- supplier capacity expansion,
- lead-time or availability constraints,
- qualification / certification barriers,
- pricing or contract repricing,
- physical / industry statistics,
- management operating commentary,
- competitor corroboration.

At least one item should come from outside the candidate beneficiary itself. Self-promotional company commentary alone cannot approve an edge.

Historical validation must use an `as_of` cutoff so evidence published after a later large contract or earnings surprise cannot leak backward into a pre-news decision.

## 5. Pre-News Chain Selector

The selector borrows the useful parts of long-term/value-investing frameworks while remaining deterministic and auditable.

Every node receives six 0-5 assessments:

1. **Demand Transmission** — how mechanically the root demand shock forces demand into this node.
2. **Bottleneck Strength** — supply elasticity, lead time, capacity difficulty, qualification barriers, concentration.
3. **Economic Capture** — pricing power, margins, switching costs, contractual position, competitive advantage.
4. **Reinvestment Runway** — ability to deploy capital into the opportunity at attractive incremental economics.
5. **Triangulation** — independent customer/supplier/competitor/physical corroboration.
6. **Expectation Gap** — strength of the economic implication relative to current market attention and consensus recognition.

The ranking score is a research-priority score, not an intrinsic-value estimate and not a buy signal.

Default weighting:

```text
Demand Transmission  20%
Bottleneck Strength  20%
Economic Capture     20%
Reinvestment Runway  15%
Triangulation        15%
Expectation Gap      10%
```

Hard gates prevent a high weighted average from hiding a weak causal link:

- demand transmission >= 3,
- at least two independent evidence classes,
- at least one externally corroborating evidence item,
- no unresolved look-ahead / timestamp violation.

Research priority stages:

- `hypothesis`: causal idea only,
- `evidence_backed`: passes causal/evidence gates,
- `priority_research`: strong bottleneck/capture economics,
- `pre_news_candidate`: strong economics plus a meaningful expectation gap.

## 6. Contract-independent evidence

The system should deliberately prefer evidence that can exist before a headline contract or explosive earnings print.

Examples:

- customer multi-year capex plans,
- rising power / compute / capacity requirements,
- facility announcements before utilization ramps,
- supplier lead-time extension,
- qualification queues,
- capacity-addition lead times,
- capex and hiring ahead of revenue,
- pricing discipline,
- working-capital build consistent with capacity preparation,
- physical industry data.

A large contract may later confirm the thesis, but it should not be required to create the original candidate.

## 7. Company Mapping

Only after a node becomes `priority_research` or `pre_news_candidate` do we map listed companies to the node.

Repo A evaluates exposure relevance rather than valuation:

- revenue / product exposure to the node,
- owned capacity,
- qualification position,
- customer concentration,
- competitive position,
- ability to expand capacity,
- evidence that the company participates in the identified bottleneck.

A company that simply lagged its peers is not automatically attractive. The system must explain why the lag is inconsistent with its economic exposure rather than treating underperformance as cheapness.

## 8. Repo B handoff

Repo A hands off only a small thesis manifest:

```json
{
  "theme": "...",
  "root_demand_shock": "...",
  "value_chain_node": "...",
  "candidate": "...",
  "demand_transmission": 0,
  "bottleneck_strength": 0,
  "economic_capture": 0,
  "reinvestment_runway": 0,
  "triangulation": 0,
  "expectation_gap": 0,
  "evidence_refs": [],
  "causal_path": []
}
```

Repo B remains responsible for financial risk, company deep research, valuation, DCF, and the final investment judgment.

## Development order

### Stage A — Provider-independent causal core

- frozen data contracts for graph edges, evidence, node assessments, and pre-news ranking,
- deterministic hard gates and scoring,
- look-ahead-safe `as_of` handling,
- synthetic regression tests.

### Stage B — Market trigger

- add price-history ingestion,
- industry/subindustry breadth aggregation,
- deterministic market-trigger output,
- historical trigger validation.

### Stage C — Causal diagnosis

- reuse current AtomicSignal scanners,
- add document-source-agnostic operating evidence,
- classify `structural_operating` vs `narrative_led`.

### Stage D — Value-chain expansion

- graph storage,
- candidate edge generation,
- evidence-backed edge approval,
- customer/supplier triangulation.

### Stage E — Pre-news validation

For historical themes, freeze an `as_of` date before the obvious confirmation event. Ask whether the system could have produced the eventual important value-chain node using only information available at that cutoff.

Validation is therefore not "did the stock later go up?" The first gate is whether the causal/economic node was discoverable without look-ahead. Investment returns belong to a later research question.

## Design invariants

- Market motion starts research; it does not validate the thesis.
- No edge is approved from LLM reasoning alone.
- No candidate is promoted from a single beneficiary's self-description alone.
- Large contracts and earnings surprises are confirmation events, not required discovery inputs.
- Exact evidence timestamps are first-class data.
- Scanner/provider gaps never silently shrink the economic hypothesis.
- Market-attention gaps rank research priority; they do not substitute for valuation.
- Repo A discovers economic exposure. Repo B underwrites the security.
