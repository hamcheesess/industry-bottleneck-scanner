# Phase 1 validation strategy

## Why the first pilot is not enough

The initial power-infrastructure pilot is a bounded known-domain recovery test. It is useful for validating transcript availability, provenance, scanner behavior, aggregation, and false acceleration caused by cohort mismatch. It is not a sufficient proof that the discovery engine can discover anomalous clusters without prior industry knowledge.

The first real prevalence-aware rerun produced flat company breadth, one positive metric-prevalence change (`backlog_strength`), no company-metric intensity increase, and no triggered or confirmed cluster. The correct response is to preserve that negative result rather than relax trigger thresholds.

## Phase 1 viability gate

The discovery engine now emits a deterministic next-gate recommendation:

- `phase2_validation` when at least one cluster is `triggered` or `confirmed`.
- `expand_neutral_cohort` when evidence remains only `observing` or `watchlisted`.

The discovery score ranks clusters inside those explicit stages. It does not override Demand + Scarcity requirements, independent-company breadth, or prevalence gates.

## Neutral matched-cohort experiment

Before Phase 2, a negative or weak known-domain pilot should be followed by a broader industry-neutral matched cohort.

Selection rules:

1. selection may use company identity and classification metadata only;
2. scanner output, prior signal scores, known bottleneck labels, and investment opinions must not affect sampling;
3. sample across multiple sectors;
4. cap representation from any one industry;
5. use a stable seed so the sample is reproducible;
6. request the same two fiscal-quarter labels for each selected issuer;
7. align the experiment again after collection so only issuers with both current and baseline transcripts enter acceleration calculations.

The `ibs-neutral-cohort-plan` command implements the deterministic sampling and paired request manifest. A default target of ten issuers creates twenty ticker-quarter requests, keeping the experiment bounded while materially broadening the original four-company matched pilot.

## What constitutes Phase 1 success

Phase 1 does not need to prove an investment thesis. It needs to demonstrate that the discovery engine can surface an auditable cross-company operating anomaly without being told the winning industry in advance.

A Phase 1 success candidate therefore requires:

- a triggered or confirmed cluster under unchanged production gates;
- matched current/baseline company coverage;
- evidence from multiple independent issuers;
- preserved metric/category prevalence deltas;
- evidence provenance sufficient for manual inspection;
- no dependence on raw mention-count inflation;
- no automatic taxonomy mutation from semantic-only language.

If those conditions hold, Phase 2 should validate the cluster with public/physical KPIs and customer-supplier triangulation. If they do not, Phase 1 remains in discovery calibration.
