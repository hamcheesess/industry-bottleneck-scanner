# V2 blind discovery / ranking rubric — draft

Status: **draft only; not frozen and not executable**.

The blind test asks whether an outcome-blind broad-US cohort surfaces a plausible emerging cluster without handpicking a known theme. It is a discovery/ranking evaluation, not a binary known-positive recall test.

## Pre-scan freeze

Before any blind scanner output is inspected, freeze:

- cohort membership and deterministic sampling seed,
- current and baseline windows,
- aggregation level,
- transcript source policy and fallback hierarchy,
- scanner/pipeline fingerprint,
- ranking formula and stage precedence,
- post-scan external-review rubric.

No issuer, window, source, threshold, or ranking term may be changed because of the observed blind result.

## Ranking unit

The ranking unit is the aggregated cluster/bucket, not an individual company.

Use existing deterministic discovery ranking. Stage precedence remains:

`confirmed > triggered > watchlisted > observing`.

Within stage, use the existing discovery score and its already-declared components. Provider identity or provider diversity must **not** improve a cluster's ranking; provider mix is provenance, not economic corroboration.

## Review set

Post-scan external review examines:

1. every watchlisted-or-stronger cluster, and
2. if none exists, the top three observing clusters by frozen discovery score.

This prevents a no-trigger run from escaping calibration review while avoiding outcome-aware expansion of the review set.

## Post-scan support labels

Each reviewed cluster receives exactly one label:

### supported

Independent external evidence is directionally consistent with the surfaced phenomenon and cluster during the tested current window. The draft target is at least two independent corroborating sources, with at least one source not originating from a company whose transcript contributed to the cluster.

### unsupported

Credible external evidence materially contradicts the surfaced phenomenon, timing, or affected cluster, or the apparent signal can be traced to a scanner/provenance correctness defect.

### indeterminate

Available evidence is insufficient, mixed, or too weak to classify supported/unsupported without changing the scanner inputs or widening the tested window.

Evidence review may use public/physical data, customer/supplier statements, industry data, or other independent public sources. It must not rewrite the blind inputs.

## Draft success interpretation

The blind dimension is provisionally successful when either:

- at least one watchlisted-or-stronger surfaced cluster is externally `supported`; or
- the run produces no watchlisted-or-stronger cluster and the reviewed top observing clusters contain no `unsupported` high-ranked false discovery or unresolved scanner correctness defect.

A no-trigger result is therefore allowed to be a calibrated result rather than an automatic failure.

## Failure / hold conditions

Hold V2 or classify the blind dimension as failed when:

- a triggered/confirmed high-ranked cluster is externally `unsupported`,
- a reviewed result exposes a general scanner/provenance correctness defect,
- provider/source gaps caused silent cohort shrinkage,
- the review rubric had to be changed after scanner output was inspected.

`indeterminate` evidence is reported separately and is not silently converted to success.

## Provider provenance

Mixed transcript providers across issuers are allowed only under the frozen V2 source hierarchy. Every reviewed cluster must report its issuer-level provider mix, but source-provider diversity is never counted as independent economic corroboration.

This rubric is a draft and should be frozen only together with the exact blind cohort, windows, source policy, and ranking contract.
