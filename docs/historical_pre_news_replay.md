# Historical pre-news replay contract

Status: **active Phase-5 execution contract**. The canonical roadmap remains
[`current_roadmap.md`](current_roadmap.md).

The replay answers one bounded question: could the approved causal system promote an
economically important downstream node using only evidence available at the frozen `as_of`?
Later returns and obvious confirmation events are diagnostics, not discovery inputs.

## Frozen input

`ibs-pre-news-replay` accepts `historical-pre-news-replay-input-v1` with:

- stable replay, market-trigger, and approved Root Demand Shock IDs;
- one timezone-aware `as_of` used by the root, graph, state, convergence, and ranking queries;
- explicit later-confirmation evidence IDs that must remain held out;
- one research judgment for every promoted convergence node.

Each node judgment explicitly supplies:

- bottleneck strength;
- economic capture;
- reinvestment runway;
- triangulation;
- expectation gap;
- optional supporting `CausalEvidence`.

Python does not invent these scores. Demand transmission alone comes directly from the
approved trigger branch. A judgment for a non-promoted node is rejected, and a promoted node
without a judgment blocks the replay rather than silently producing a partial ranking.

## Execution

```bash
ibs-pre-news-replay \
  --input artifacts/replay/early-ai-electrical/input.json \
  --market-trigger-artifact artifacts/market-trigger/replay-2024-11-15.json \
  --root-shock-registry artifacts/causal/root_shocks.jsonl \
  --causal-graph-registry artifacts/causal/graph.jsonl \
  --industry-state-registry artifacts/industry/industry_state.jsonl \
  --output-dir artifacts/replay/early-ai-electrical/output
```

The runner:

1. verifies that the frozen market-trigger ID matches the approved trigger root and that the
   trigger date/bucket is present in the fingerprinted market artifact;
2. loads only approved root and edge revisions visible at `as_of`;
3. joins the latest industry state strictly before the trigger;
4. promotes only non-hypothesis convergence assessments;
5. combines path, state, and explicit judgment evidence by stable evidence ID;
6. rejects evidence after `as_of` and any held-out confirmation leakage;
7. calls the existing `NodeAssessment` / `rank_nodes` logic without redefining its scores.

## Outputs

- `replay_freeze.json` — exact IDs, cutoff, holdouts, SHA-256 of every input, and a canonical
  freeze fingerprint;
- `pre_news_rankings.json` — convergence/path references, explicit scores, evidence references,
  and the existing pre-news ranking result.

A successful artifact has `status=full`. The current contract fails closed instead of emitting
`limited` when promoted-node judgments or frozen inputs are incomplete. Company exposure mapping
and the Repo-A -> Repo-B manifest remain outside this replay stage.
