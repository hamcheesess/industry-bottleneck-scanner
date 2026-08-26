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
- a second evidence class beyond issuer operating disclosures;
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
