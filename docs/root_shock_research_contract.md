# Root-shock research packet contract

The root-shock research packet is a provider-free, strict-as-of handoff between deterministic
operating-signal quality control and external causal research. It does not approve a causal
story.

`ibs-root-shock-research-packets` joins the frozen research queue, the signal-quality audit,
and the matching `OperatingSupport` artifact. For every candidate it selects a bounded set of
direct issuer disclosures while preferring scanner, metric, and issuer diversity. Repeated
same-company text and speculative risk-factor language remain in the canonical signal archive
but are excluded from the packet.

Every packet is deliberately incomplete. Approval remains false until research supplies:

- a concrete exogenous demand mechanism;
- a stable economic-node assignment independent of ticker classification;
- a second independent evidence class and at least one non-issuer source;
- external corroboration published no later than the packet `as_of`.

The builder rejects mismatched candidate sets, incomplete active-signal references, timezone-free
timestamps, and any signal later than `as_of`. Input fingerprints and source URLs are persisted so
later research can be replayed without provider access.

```bash
ibs-root-shock-research-packets \
  --causal-diagnosis-dir artifacts/causal-diagnosis \
  --operating-evidence-dir artifacts/operating \
  --quality-audit artifacts/causal-diagnosis/operating_signal_quality.json \
  --output-dir artifacts/causal-diagnosis/root-shock-research
```

## Research-result adjudication

`ibs-root-shock-research-adjudicate` validates one completed packet without modifying the
append-only root-shock registry. It copies the market-trigger identity from the frozen packet,
rejects ticker-shaped node IDs and post-cutoff sources, and requires both linked packet evidence
and at least one independent non-issuer source. Evidence classes must use the existing
`CausalEvidence` taxonomy.

An eligible result produces `root-demand-shock-input-v1`, but still does not append it. An
ineligible result overwrites the same output path with
`root-demand-shock-input-ineligible-v1`, which the existing append CLI rejects. This prevents a
stale proposal from bypassing a failed re-review.

```bash
ibs-root-shock-research-adjudicate \
  --packet artifacts/causal-diagnosis/root-shock-research/candidates/<packet-id>.json \
  --research-result artifacts/research/<packet-id>.json \
  --output-dir artifacts/causal/adjudication/<packet-id>
```
