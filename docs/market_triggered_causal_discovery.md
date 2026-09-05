# Market-triggered causal discovery roadmap

## Objective

The discovery engine does not try to predict every quiet industry before the market reacts. It starts from a visible market anomaly, determines whether the move is supported by a structural operating demand shock, then expands outward through the value chain to find economically important nodes before large contracts or explosive reported earnings make the second- and third-order beneficiaries obvious.

The core question is:

> If the observed demand shock persists, which value-chain nodes must absorb the incremental demand, where was supply already constrained before the shock, where do multiple independent demand branches converge, who can capture the economics, and which implications appear least reflected in current market attention?

## Two-loop architecture

The system has two independent loops that meet only when a new demand shock reaches a known value-chain node.

```text
LOW-FREQUENCY STATE LOOP                 EVENT-DRIVEN DISCOVERY LOOP

public operating evidence               broad-US market data
        |                                        |
        v                                        v
Persistent Industry State               Market Trigger
        |                                        |
lead time / capacity /                           v
qualification / pricing                  Causal Diagnosis
        |                                        |
        |                                        v
        |                               Root Demand Shock
        |                                        |
        +-------------------+--------------------+
                            |
                            v
                  Value-chain Expansion
                            |
                            v
                  Demand Convergence Engine
                            |
             new shock x pre-shock constraint
                  x independent demand roots
                            |
                            v
                  Pre-News Chain Selector
                            |
                            v
                 Listed-company Mapping
                            |
                            v
                       Repo B
```

This avoids two bad assumptions:

1. every industry must be continuously researched in depth; and
2. a supply bottleneck must be created by the new market theme.

A particularly attractive setup is a **new demand shock entering a node that was already constrained for unrelated reasons**.

## 1. Market Trigger

Run cheap end-of-day or weekly calculations across the broad-US universe.

Candidate trigger inputs:

- 1m / 3m / 6m return,
- market-relative and sector-relative return,
- cross-company breadth inside an industry/subindustry,
- abnormal volume,
- distance to 52-week high,
- optional later: estimate-revision breadth.

The output is an `IndustryMarketTrigger`, not a stock recommendation. A valid trigger should prefer broad industry participation over a single-stock spike.

ETF products such as SOXX may be used as corroborating market labels, but the canonical aggregation unit remains bottom-up company membership in sector / industry / economic subcluster buckets.

## 2. Causal Diagnosis

For the triggered cluster, collect inexpensive public operating evidence:

- earnings-call transcripts when available,
- earnings releases,
- 8-K / 10-Q disclosures,
- investor presentations,
- customer and supplier disclosures.

Run the existing Capex / Demand / Scarcity / Pricing scanner. The diagnosis classifies the market trigger as one of:

- `structural_operating`,
- `narrative_led`,
- `mixed_or_early`,
- `unresolved`.

A two-month-old earnings call can still be useful. It is treated as pre-existing operating state, not as proof of the immediate cause of today's market move. The discovery `as_of` timestamp determines what was knowable.

## 3. Persistent Industry State Registry

The registry is a low-frequency memory of supply-side conditions at economically meaningful value-chain nodes. It is append-only so historical replay can ask what the system knew before a later market trigger.

Each `IndustryStateSnapshot` scores six directional dimensions from 0 to 5, where higher always means tighter supply:

- supply inelasticity,
- lead-time pressure,
- capacity tightness,
- capacity-expansion difficulty,
- qualification barrier,
- pricing pressure.

A state requires at least two independent evidence classes before it can be classified as known. The deterministic stages are:

- `unknown`,
- `normal`,
- `tightening`,
- `constrained`,
- `severely_constrained`.

The key historical rule is strict: **a pre-shock state snapshot must be timestamped before the market trigger**. Evidence learned after the new theme became obvious cannot be backfilled into the prior state.

Examples of suitable state evidence include supplier capacity expansion, long lead times, qualification queues, capacity utilization, backlog/orders, pricing/repricing, physical industry data, regulatory/permitting constraints, and competitor corroboration.

## 4. Root Demand Shock

A structural market trigger is translated into a concrete economic demand shock, not a vague theme label.

Prefer:

- `AI inference compute deployment`,
- `hyperscaler data-center MW expansion`,
- `grid-hardening capital program`,

rather than simply `AI`, `cloud`, or `energy`.

This root identity matters because later convergence logic must not count multiple paths from the same shock as independent demand branches.

## 5. Value-chain Hypothesis Graph

Candidate edges may be proposed mechanically, manually, or later by an LLM, but an LLM proposal is never sufficient for approval.

Allowed edge relations stay economically explicit:

- `requires_input`,
- `requires_capacity`,
- `capacity_enabler`,
- `complement`,
- `substitute`,
- `distribution_or_service`,
- `physical_constraint`.

Each edge records the mechanism, demand sensitivity, time lag, evidence, provenance, and confidence.

The graph is intentionally many-to-many. A node can receive demand from several unrelated roots, and one root can branch into many downstream paths.

## 6. Evidence-backed Edge Approval

Every material edge must be supported by at least two independent evidence classes before it becomes a trusted research path. At least one item should come from outside the candidate beneficiary itself.

Useful evidence classes include customer capex/capacity plans, architecture dependency, supplier capacity expansion, lead-time constraints, qualification barriers, pricing/repricing, physical industry statistics, management commentary, and competitor corroboration.

This prevents vague chains such as `AI -> electricity -> copper -> miner` from being promoted without an explicit economic mechanism.

## 7. Demand Convergence Engine

This is the main addition to the architecture.

The engine asks whether a newly detected demand root reaches a node that satisfies two separate conditions:

1. the node was already `constrained` or `severely_constrained` before the trigger; and
2. the new root joins one or more economically independent demand roots at the same node.

Example:

```text
grid modernization -----------\
cloud data-center growth -------+--> large power transformers
AI inference buildout ----------/         |
                                          +--> pre-shock state: constrained
```

The attractive fact is not merely that AI needs transformers. It is that a new AI-related demand branch may enter a shared trunk whose supply was already tight because of other demand sources.

Multiple paths from the same root shock do **not** count as independent roots. For example, `AI -> GPU cluster -> data center -> transformer` and `AI -> networking -> data center -> transformer` remain one `AI` root for convergence breadth.

Current deterministic convergence stages are:

- `hypothesis`: pre-shock state absent/normal or the new branch is weak,
- `pre_shock_bottleneck`: one strong new demand root reaches a previously constrained node,
- `multi_branch_convergence`: at least two independent roots share the constrained node,
- `priority_convergence`: strong new transmission plus multi-root convergence and a high structural score.

A large contract is not required.

## 8. Pre-News Chain Selector

After a node passes structural convergence, it is assessed on six 0-5 dimensions:

1. **Demand Transmission**
2. **Bottleneck Strength**
3. **Economic Capture**
4. **Reinvestment Runway**
5. **Triangulation**
6. **Expectation Gap**

Default weighting:

```text
Demand Transmission  20%
Bottleneck Strength  20%
Economic Capture     20%
Reinvestment Runway  15%
Triangulation        15%
Expectation Gap      10%
```

Hard gates prevent a high weighted average from hiding a weak causal link. The score is a research-priority score, not a valuation and not a buy signal.

## 9. Contract-independent evidence

The system deliberately prefers evidence that can exist before a headline contract or explosive earnings print:

- customer multi-year capex plans,
- rising power / compute / capacity requirements,
- facility announcements before utilization ramps,
- supplier lead-time extension,
- qualification queues,
- capacity-addition lead times,
- capex and hiring ahead of revenue,
- backlog/order changes,
- pricing discipline,
- working-capital build consistent with capacity preparation,
- physical industry data.

A later contract may confirm the thesis, but it should not be needed to create the original candidate.

## 10. Company Mapping and Repo B

Only after a node becomes structurally important do we map listed companies to it. Repo A evaluates exposure relevance rather than valuation:

- product/revenue exposure,
- owned capacity,
- qualification position,
- competitive position,
- expansion ability,
- evidence that the company participates in the identified bottleneck.

A lagging stock is not automatically attractive.

Repo B remains responsible for financial risk, company deep research, valuation, DCF, and the final investment judgment.

## Historical validation

The first serious replay should test whether the system could have constructed a chain such as `AI compute -> data-center capacity -> electrical infrastructure -> constrained transformer/electrical nodes` using only information available before obvious downstream confirmation events.

Validation must freeze:

- market-trigger timestamp,
- root demand shock definition,
- pre-shock registry snapshot,
- allowed evidence cutoff,
- graph paths,
- later confirmation event held out from discovery.

The first question is not whether the stock later rose. It is whether the causal convergence node was discoverable without look-ahead.

## Development order

### Stage A — completed provider-independent core

- causal evidence and value-chain edge contracts,
- pre-news node ranking,
- market-trigger breadth core,
- persistent industry-state registry,
- multi-root demand convergence engine,
- look-ahead-safe synthetic regression tests.

### Stage B — next

- free/low-cost end-of-day price-history ingestion,
- real industry/subindustry market-trigger generation,
- source-agnostic operating evidence ingestion beyond transcripts,
- state-registry update jobs from public disclosures,
- graph persistence and approved-edge artifacts.

### Stage C — historical replay

- freeze an early AI-cycle `as_of` case,
- reconstruct pre-shock electrical/transformer state,
- replay market trigger and causal expansion,
- measure when shared constrained nodes became discoverable,
- hold later contracts/earnings surprises out as confirmation only.
