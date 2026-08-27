# Root-shock and causal-convergence contract

Status: **active Phase-4 contract**. The canonical roadmap remains
[`current_roadmap.md`](current_roadmap.md).

## Root Demand Shock

A `RootDemandShock` is a concrete economic demand event, not a theme label. Each revision
records:

- stable `root_shock_id` and economic `root_node`;
- concrete label and transmission mechanism;
- originating market-trigger ID and bucket;
- trigger detection timestamp and research `as_of`;
- 0–5 demand strength;
- evidence with source and observation timestamps.

Approval fails closed when demand strength is below 3, fewer than two evidence classes are
present, external corroboration is absent, or any evidence is later than `as_of`. Approved and
rejected revisions are both preserved in the append-only `root-demand-shock-v1` registry; the
latest revision visible at replay time controls eligibility.

```bash
ibs-root-shock-append \
  --input artifacts/causal/root_shock_input.json \
  --registry artifacts/causal/root_shocks.jsonl
```

The input uses `root-demand-shock-input-v1`. Creating the concrete shock and supplying its
evidence remains a research decision; an LLM may propose it but cannot bypass approval.

## Causal-edge approval

`ibs-causal-edge-append` evaluates one dated `causal-edge-input-v1` revision and appends the
approved or rejected decision to the graph history. Approval requires at least two independent
evidence classes, external corroboration, a concrete economic mechanism, and no evidence observed
after the revision `as_of`. Duplicate `(edge_id, as_of)` revisions are rejected.

The first curated edge is
`experiments/causal_edges/ai-data-center-load-to-grid-interconnection.json`. It connects the
approved `ai-data-center-electric-load-growth` root to the economic node
`large-load-grid-interconnection-capacity`, using dated DOE physical-load evidence, the NERC large-
load integration filing, and Arcosa utility-structure backlog. It does not infer a second edge to
a specific equipment or company node.

```bash
ibs-causal-edge-append \
  --input experiments/causal_edges/ai-data-center-load-to-grid-interconnection.json \
  --registry artifacts/causal/graph.jsonl
```

`.github/workflows/causal-edge-adjudication.yml` reproduces that evaluation and can optionally
extend an exact prior graph artifact without weakening the append-only or strict-as-of gates.

The second curated edge is
`experiments/causal_edges/grid-interconnection-to-large-power-transformers.json`. It extends only
one segment, from `large-load-grid-interconnection-capacity` to `large-power-transformers`.
DOE's July 2024 LPT report supplies the grid-expansion mechanism, while Hitachi Energy's April
2024 factory announcement independently identifies LPTs as grid-interconnection and data-center
components and records a North American capacity response. The edge does not infer any listed
company exposure or add an independent demand root.

## Approved path expansion

`ibs-causal-convergence` composes existing stores without modifying their domain logic:

```text
approved root shocks as_of T
  + approved graph edges as_of T
  -> bounded cycle-safe paths
  -> DemandBranch artifacts
  + latest IndustryStateSnapshot strictly before trigger
  -> DemandConvergenceAssessment
```

Branch IDs are stable hashes of `(root_shock_id, path_nodes)`. Branch transmission strength is
the minimum of root strength and the strongest approved edge for every path segment. This avoids
allowing one weak segment to disappear inside an average. Evidence is deduplicated by stable ID.

Multiple paths from one root remain multiple auditable branches but count as only one independent
root in convergence scoring. Only targets reached by the currently triggered root are assessed.

```bash
ibs-causal-convergence \
  --root-shock-registry artifacts/causal/root_shocks.jsonl \
  --causal-graph-registry artifacts/causal/graph.jsonl \
  --industry-state-registry artifacts/industry/industry_state.jsonl \
  --trigger-root-shock-id ai-inference-deployment-2026q3 \
  --as-of 2026-08-21T23:59:59+00:00 \
  --output-dir artifacts/causal/convergence
```

Outputs:

- `demand_branches.jsonl` — `demand-branch-v1` path and evidence references;
- `demand_convergence.json` — `causal-convergence-run-v1` assessments and strict pre-shock
  state references.

`.github/workflows/causal-convergence-production.yml` supports two explicit validation profiles.
`first_path_hypothesis` preserves the original one-edge fail-closed result.
`transformer_pre_shock_bottleneck` requires exactly the two approved paths, keeps the
grid-interconnection assessment at `hypothesis`, requires the transformer state to be exactly
`severely_constrained` at 84 points, and verifies that only the original demand root is present.
Unknown profiles fail closed.

Future root, edge, evidence, and industry-state revisions are excluded by their timestamped
registries. The artifacts are therefore suitable inputs for historical pre-news replay.
