# Later-confirmation holdout contract

Status: **active Phase-5 contract**. The canonical roadmap remains
[`current_roadmap.md`](current_roadmap.md).

The historical replay and later confirmation answer different questions. The replay asks what the
system could have known at `2026-08-21`. The holdout asks whether that already-frozen industrial
thesis subsequently behaved as expected. Later evidence may confirm or weaken the thesis, but it
must never be fed back into the old ranking as if it had been known at the cutoff.

## Why this boundary exists

The two-root replay selected `large-power-transformers` because two evidence-disjoint demand paths
reached a severely constrained node. It did not prove that announced projects would become actual
orders, that the bottleneck would persist after supply expansion, or that suppliers would retain
the resulting economics. These are observable future claims. Their questions, windows, source
classes, independence requirements and falsifiers must therefore be written down before the
relevant results arrive.

The contract separates five dimensions:

| Dimension | Window | Purpose | Initial status |
|---|---:|---|---|
| Demand realization | 90 days | Test whether plans become orders, projects and backlog | `pending` |
| Bottleneck persistence | 180 days | Test whether lead times, slots, qualification and materials remain constrained | `pending` |
| Supply response | 365 days | Test whether effective capacity catches demand after ramp and qualification | `pending` |
| Economic capture | 180 days | Test whether scarcity reaches price, mix, margin, terms or cash returns | `pending` |
| Security expectation gap | not recoverable | Requires a pre-cutoff basket, price/valuation and consensus snapshot | `blocked` |

The blocked expectation slot is deliberate. No transformer security basket and expectation
snapshot was frozen before the replay cutoff. Reconstructing one after observing later price or
fundamental outcomes would create hindsight. Industry confirmation can proceed, but this artifact
cannot issue a buy/sell conclusion or claim that the market was wrong.

## Frozen plan

`experiments/later_confirmation/large-power-transformers-2026-08-21.json` uses
`later-confirmation-plan-v1`. A valid plan must:

- bind to exactly one full replay result, replay ID, node and cutoff;
- be frozen after the replay cutoff while every observation window begins strictly after it;
- declare allowed source classes and minimum independent entity/source-class counts in advance;
- state reader-facing confirmation, warning and break definitions;
- keep `automatic_rerank=false` and `security_level_conclusion=false`;
- mark unavailable prerequisites as non-required and explain why they are blocked.

The validator canonicalizes this input and adds `plan_sha256`. Editing a question, date,
threshold or falsifier changes the fingerprint.

## Evidence and diagnosis

Optional `later-confirmation-evidence-v1` records contain a stable evidence ID, slot ID,
observation time, source, source class, source entity, direction and factual summary. The builder
rejects:

- evidence at or before the replay cutoff;
- evidence after the evaluation time or outside the slot's frozen window;
- unknown slots, blocked slots, duplicate evidence IDs or unapproved source classes;
- records that fail the predeclared entity/source diversity requirements for a complete result.

A slot is `pending`, `partial`, `confirmed`, `disconfirmed`, `mixed` or `blocked`. The node-level
diagnostic becomes `confirmed` only when all four required industrial slots are confirmed. A
disconfirmed required slot yields `weakening`; conflicting complete evidence yields `mixed`.
Sparse evidence remains `partial` rather than being treated as confirmation.

The diagnostic always preserves the original 73.0 `evidence_backed` ranking and the 75.07
`priority_convergence` assessment as audit references. `original_replay_unchanged=true` is an
invariant, not a display preference.

## Reader-facing output

```bash
ibs-later-confirmation \
  --plan experiments/later_confirmation/large-power-transformers-2026-08-21.json \
  --replay-result artifacts/replay/pre_news_rankings.json \
  --evaluation-as-of 2026-08-29T23:59:59+00:00 \
  --output-dir artifacts/later-confirmation
```

The command writes a structured JSON diagnostic and a Korean Markdown report. The report explains
the industrial question behind every slot, its observation window, the minimum independent
support, and the exact facts that would confirm, warn or break the thesis. A score-only monitoring
artifact is not accepted.

`.github/workflows/later-confirmation-production.yml` downloads the exact two-root replay artifact,
checks the unchanged ranking and cutoff, creates the initial empty diagnostic, verifies all four
industrial slots are pending and the expectation gap is blocked, writes provenance, and uploads a
90-day artifact. It performs no provider calls and does not authorize company mapping.
