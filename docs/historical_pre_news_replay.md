# Historical pre-news replay contract

Status: **active Phase-5 execution contract**. The canonical roadmap remains
[`current_roadmap.md`](current_roadmap.md).

The replay answers one bounded question: could the approved causal system promote an
economically important downstream node using only evidence available at the frozen `as_of`?
Later returns and obvious confirmation events are diagnostics, not discovery inputs.

A numerical ranking is not a complete product output. Every production replay must also emit a
reader-facing Korean industry analysis that explains what the economic node does, where demand
comes from, how demand reaches the node, why supply is constrained, what can relieve the
constraint, whether the economics can be captured, what the score does and does not mean, and
what would falsify the view.

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

The companion `ibs-industry-analysis-report` command then validates a committed
`industry-analysis-narrative-input-v1` against the exact replay result and freeze. Every factual
or inferential narrative block references evidence IDs already admitted by the replay. Unknown
IDs, post-cutoff observations, a mismatched replay/freeze, or a missing required section fail the
build.

```bash
ibs-industry-analysis-report \
  --analysis-input experiments/industry_analysis/large-power-transformers-2026-08-21.ko.json \
  --replay-result artifacts/replay/pre_news_rankings.json \
  --replay-freeze artifacts/replay/replay_freeze.json \
  --output-dir artifacts/replay
```

## Outputs

- `replay_freeze.json` — exact IDs, cutoff, holdouts, SHA-256 of every input, and a canonical
  freeze fingerprint;
- `pre_news_rankings.json` — convergence/path references, explicit scores, evidence references,
  and the existing pre-news ranking result.
- `industry_analysis.json` — evidence-bound structured narrative, score explanations, scenarios,
  limitations, and report fingerprint;
- `industry_analysis.ko.md` — the first-read Korean industry report. The score is a supporting
  table, not the report's conclusion.

A successful artifact has `status=full`. The current contract fails closed instead of emitting
`limited` when promoted-node judgments or frozen inputs are incomplete. Company exposure mapping
and the Repo-A -> Repo-B manifest remain outside this replay stage.

## First production case

The first bounded production input is
`experiments/pre_news_replay/early-ai-electrical-2026-08-21.json`. The reusable and manually
dispatchable `.github/workflows/pre-news-replay-production.yml` pins the exact provider-free
market, root, graph, and state run IDs and refuses any unsupported validation profile.

The `2026-08-21` replay produced one ranked economic node:

- `large-power-transformers`;
- convergence stage `pre_shock_bottleneck` from one approved root;
- 14 evidence records across eight evidence classes;
- frozen scores `4/5/2/4/5/1` for demand transmission, bottleneck strength, economic capture,
  reinvestment runway, triangulation, and expectation gap;
- final score `73.0`, stage `evidence_backed`;
- latest accepted evidence at `2026-08-06T20:13:52+00:00`, before the replay cutoff;
- automatic company mapping and automatic `pre_news_candidate` promotion both disabled.

The same workflow now requires the committed Korean transformer analysis. It explains all 14
frozen evidence records, separates facts from inference and uncertainty, includes base/upside/
downside paths and falsifiers, and explicitly states that the 73.0 score is neither a success
probability nor a security recommendation.

Every reader-facing report must begin by explaining why the economic node entered research. The
selection section is not free-form hindsight: it joins the exact market-trigger artifact already
fingerprinted by the replay freeze with the outcome-blind quality review, shows observed breadth
and attention metrics against the frozen thresholds, records trigger persistence, and then quotes
the issuer operating phrases that moved the bucket from market anomaly to causal investigation.
It must explicitly distinguish the originating market bucket from the downstream bottleneck node.

## Independent-root production replay

The versioned second input is
`experiments/pre_news_replay/early-ai-electrical-2026-08-21-two-root.json`. It preserves the first
AI-load path and adds the evidence-disjoint `grid-modernization-and-resilience-investment-2026q3`
root with a direct path to `large-power-transformers`.

The exact production replay requires:

- convergence stage `priority_convergence` at 75.07 from exactly two independent roots;
- the unchanged 84-point `severely_constrained` pre-trigger transformer state;
- exactly two transformer path sequences and no future evidence;
- 17 evidence records across eight evidence classes;
- the unchanged frozen node scores `4/5/2/4/5/1`, final score 73.0 and stage
  `evidence_backed`;
- a Korean report that explains both demand paths and all 17 admitted evidence records.

Structural convergence does not change the economic-capture or expectation-gap judgments. The
second replay therefore raises research priority without authorizing company mapping or a
security-level conclusion.

The first input has no identified post-trigger confirmation evidence yet, so its held-out list is
empty. That does not weaken the cutoff gate: any evidence after `as_of` is still rejected. It does
mean later-outcome diagnostics remain incomplete and must not be inferred from `status=full`.
