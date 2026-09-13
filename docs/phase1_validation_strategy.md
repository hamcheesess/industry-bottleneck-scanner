# Phase 1 validation strategy

## Why the first pilot is not enough

The initial power-infrastructure pilot is a bounded known-domain recovery test. It is useful for validating transcript availability, provenance, scanner behavior, aggregation, and false acceleration caused by cohort mismatch. It is not a sufficient proof that the discovery engine can discover anomalous clusters without prior industry knowledge.

The first real prevalence-aware rerun produced flat company breadth, one positive metric-prevalence change (`backlog_strength`), no company-metric intensity increase, and no triggered or confirmed cluster. The correct response is to preserve that negative result rather than relax trigger thresholds.

## Phase 1 viability gate

The discovery engine now emits a deterministic next-gate recommendation:

- `phase2_validation` when at least one cluster is `triggered` or `confirmed`.
- `expand_neutral_cohort` when evidence remains only `observing` or `watchlisted`.

The discovery score ranks clusters inside those explicit stages. It does not override Demand + Scarcity requirements, independent-company breadth, or prevalence gates.

## Expanded validation order

Before Phase 2, validation runs in three frozen stages:

1. predeclared known-positive recovery cases;
2. matched negative controls;
3. a blind industry-neutral cohort selected without scanner outcomes.

The labeled evaluator measures known-positive recovery, expected-metric recovery, and false positives on controls. Blind cases remain diagnostic until scanner output is frozen and external validation begins.

Default development gates are positive recovery recall >= 67%, expected-metric recall >= 67%, and negative-control false-positive rate <= 20%. These are validation gates, not knobs that are tuned after looking at one result.

## Approved validation-only broad-US proxy

For Phase-1 validation only, exact Russell 3000 constituent membership is not required. The approved policy is to use a free broad-U.S. proxy so discovery quality can be tested before paying for canonical constituent data.

The default proxy source is the public iShares Russell 3000 ETF (`IWV`) holdings CSV. It is suitable for this narrow purpose because it is a broad U.S. equity portfolio designed to track the Russell 3000 benchmark and exposes a dated holdings file with ticker, sector, asset class, location, and exchange. It is **not** canonical Russell 3000 membership and must never be labeled or persisted as such.

`ibs-neutral-proxy-iwv` downloads the current public holdings CSV, keeps U.S. equity rows, records the holdings as-of date and source URL, and writes a candidate file for the neutral cohort planner. The generated provenance explicitly sets `canonical_russell_3000=false` and `purpose=phase1_validation_only`.

`ibs-phase1-proxy-plan` performs the download and blind-cohort sampling in one command. The plan records the stable seed, the selected groups, the paired current/baseline requests, and the fact that scanner outcomes were not used in selection.

IWV holdings expose sector but not granular industry classification in the public CSV. The proxy importer therefore writes an explicit `proxy-sector::<sector>` value into the cohort `industry` field only to satisfy the generic cohort contract. This is a machine-visible placeholder, not a claim of granular industry knowledge.

Because the public proxy classification is sector-only, the resulting blind proxy experiment must use `aggregation_level=sector`. The plan writes `recommended_aggregation_level=sector`. Production industry-level discovery remains unchanged and must use a source with genuine industry classifications.

Production discovery now uses the separately approved `broad_us_common_stocks_v1` contract.
Passing historical Phase-1 transcript validation with the IWV proxy does not authorize ETF
holdings as production membership.

## Trigger-reachable blind cohort

A blind sample must not make the production trigger mathematically impossible. Since the Phase-1 trigger requires at least three independent companies inside one aggregation bucket, a sampler that spreads one or two companies across many industries cannot validate discovery behavior.

The neutral sampler therefore selects classification groups first and then selects enough issuers inside each group. Defaults are three groups with four companies per group. For a fully available two-window experiment this yields 12 issuers and 24 ticker-quarter transcript requests. The extra company above the three-company minimum provides one unit of coverage slack without relaxing the production trigger.

Selection rules:

1. selection may use company identity and classification metadata only;
2. scanner output, prior signal scores, known bottleneck labels, and investment opinions must not affect sampling;
3. selected groups should span multiple sectors when genuine industry labels are available;
4. every selected aggregation group must contain at least three issuers;
5. use a stable seed so the sample is reproducible;
6. request the same two fiscal-quarter labels for each selected issuer;
7. align the experiment again after collection so only issuers with both current and baseline transcripts enter acceleration calculations.

## What constitutes Phase 1 success

Phase 1 does not need to prove an investment thesis. It needs to demonstrate that the discovery engine can surface an auditable cross-company operating anomaly without being told the winning industry in advance.

A Phase 1 success candidate therefore requires:

- labeled recovery gates pass without changing production thresholds after seeing results;
- negative controls remain within the false-positive limit;
- a blind cohort produces a plausible nontrivial ranking rather than everything or nothing firing;
- any Phase-2 candidate is triggered or confirmed under unchanged production gates;
- matched current/baseline company coverage;
- evidence from multiple independent issuers;
- preserved metric/category prevalence deltas;
- evidence provenance sufficient for manual inspection;
- no dependence on raw mention-count inflation;
- no automatic taxonomy mutation from semantic-only language.

If those conditions hold, Phase 2 should validate the cluster with public/physical KPIs and customer-supplier triangulation. If they do not, Phase 1 remains in discovery calibration.
