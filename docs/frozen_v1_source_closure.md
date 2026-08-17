# Frozen v1 source-coverage closure

Frozen v1 is intentionally preserved as an Alpha Vantage-only transcript experiment.

The source contract is not expanded after outcomes are observed. Provider-missing ticker-quarter requests remain source-coverage limitations; they are not silently replaced with another transcript provider, removed from the blind cohort, or relabeled as negative evidence.

A terminal provider-missing state therefore closes frozen v1 as source-coverage-limited rather than creating another collection loop. The incomplete blind case cannot be scored, so the full frozen-v1 gate is not evaluable and Phase 2 remains blocked.

The fresh labeled/control subset remains diagnostic. Scanner vocabulary, semantic thresholds, aggregation thresholds, and trigger thresholds stay frozen. The observed false-positive control is retained for the whole-system review rather than tuned away.

The next design step is a separately versioned v2 validation contract. V2 may use a predeclared multi-source fallback policy, but that source policy must be frozen before outcomes are inspected. Frozen v1 remains the audit trail of the single-source experiment.
