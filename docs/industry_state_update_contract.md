# Industry-state update contract

Status: **active Phase-3 contract**. The canonical roadmap remains
[`current_roadmap.md`](current_roadmap.md).

## Purpose

`IndustryStateSnapshot` records the constraint state of an economic value-chain node before a
later market shock. It is not a company score and its `node_id` must never be inferred from a
ticker or static industry label.

```text
AtomicSignal + explicit issuer-to-node assignment
  -> IndustryStateObservation

external physical / industry evidence
  -> IndustryStateObservation

evidence-diversity gate + prior snapshot
  -> append-only IndustryStateSnapshot
```

## Deterministic issuer-signal mapping

Only operating metrics with a defensible state meaning are mapped automatically:

| AtomicSignal metric | State dimension | Evidence class |
|---|---|---|
| `lead_time_pressure` | `lead_time_pressure` | `lead_time_constraint` |
| `capacity_constraint`, `sold_out_capacity` | `capacity_tightness` | `capacity_utilization` |
| `supply_tightness`, `allocation` | `supply_inelasticity` | `management_operating_commentary` |
| `qualification_barrier` | `qualification_barrier` | `qualification_barrier` |
| pricing/repricing metrics | `pricing_pressure` | `pricing_or_repricing` |

Backlog, bookings, and capex announcements are not silently converted into supply constraints.
Negated or resolved signals are excluded. The caller must provide an explicit many-to-many
`company_id,node_id` assignment.

## Approval gate

A candidate update is appended only when all conditions hold:

- at least one new observation exists;
- all observation timestamps are at or before the timezone-aware update `as_of`;
- at least two independent evidence classes support the snapshot;
- at least two independent source entities support it;
- it changes scores or adds evidence relative to the prior snapshot;
- the `(node_id, as_of)` key does not already exist.

Multiple documents from one issuer count as one source entity. Evidence without a
`source_company_id`, such as public physical datasets, is identified by its source ID. Rejected
updates are emitted as decisions but are not recorded as known state.

Unobserved dimensions carry forward from the latest earlier snapshot. There is deliberately no
automatic time decay yet; the roadmap requires replay evidence before a decay policy is added.

## Execution

External observations use `industry-state-observation-v1` JSONL. Issuer observations can be
derived directly from the `atomic_signals.jsonl` artifact plus explicit node assignments:

```bash
ibs-industry-state-update \
  --atomic-signals-jsonl artifacts/operating/atomic_signals.jsonl \
  --node-assignments-csv artifacts/research/company_node_assignments.csv \
  --observations-jsonl artifacts/industry/physical_observations.jsonl \
  --as-of 2026-08-21T23:59:59+00:00 \
  --registry artifacts/industry/industry_state.jsonl \
  --decisions artifacts/industry/state_update_decisions.json
```

The external-observation file is optional when issuer signals are supplied, and vice versa.
The decisions artifact records approvals, rejection reasons, source/evidence diversity, the
prior snapshot reference, and the complete candidate snapshot.
