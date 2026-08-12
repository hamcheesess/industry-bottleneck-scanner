# Phase 1 Expansion Validation Protocol

## Purpose

Phase 1 is not considered validated merely because transcript collection and signal extraction run successfully. The discovery engine must demonstrate that it can recover known operating bottlenecks, avoid firing on negative controls, and surface plausible clusters in an industry-neutral sample without using the expected outcome during selection.

The validation sequence is deliberately ordered to separate recall, precision, and discovery behavior.

## Stage A — known-positive recovery

Use historical periods where a bottleneck or demand/supply imbalance is independently documented outside the scanner.

Each positive case records before the run:

- a case identifier
- the expected classification bucket
- a bounded current/baseline comparison window
- the expected signal metrics that should be recoverable from management language
- source notes documenting why the case was labeled positive

Labels must be frozen before scanner output is inspected. A positive case is recovered only when the expected bucket reaches at least `watchlisted` and all predeclared expected metrics are present in the current-window active metrics.

The purpose is to test whether the vocabulary/retrieval stack can recover a real phenomenon, not whether thresholds can be tuned until a selected example fires.

## Stage B — negative controls

Controls should be selected from comparable listed companies or industries where the predeclared period does not contain the target bottleneck pattern. Selection should match source type and temporal coverage as closely as practical.

A control is counted as a false positive if any cluster reaches `triggered` or `confirmed`. `observing` and `watchlisted` states remain diagnostic and are not counted as production false positives.

## Stage C — blind industry-neutral cohort

Blind cases have no expected bucket and do not contribute to label-based pass/fail metrics. They are selected deterministically from identity/classification metadata only, using `ibs-neutral-cohort-plan`, before transcript signals are inspected.

The blind cohort is used to inspect:

- which clusters rank highest without theme preselection
- stage distribution (`observing`, `watchlisted`, `triggered`, `confirmed`)
- concentration by sector/industry
- whether one issuer or one metric dominates a result
- whether novel-language candidates repeat across independent companies

Blind outcomes should be reviewed against external evidence only after the scanner output is frozen.

## Validation metrics

`ibs-phase1-validate` evaluates a CSV manifest pointing to completed `ibs-phase1-batch` result JSON files.

Primary metrics:

- positive recovery recall
- expected-metric recall
- control false-positive rate

Default viability thresholds are intentionally explicit rather than hidden in a composite score:

- positive recovery recall >= 67%
- expected-metric recall >= 67%
- control false-positive rate <= 20%

These are development gates, not claims of statistical significance. They should be revisited only after sample size expands; they must not be changed merely to make a failing cohort pass.

## Manifest format

```csv
case_id,role,result_path,expected_bucket,expected_metrics,notes
power-positive,positive,var/validation/power-positive.json,Electrical Equipment,backlog_strength|capacity_constraint,labels frozen before run
matched-control,control,var/validation/control.json,,,matched source coverage
blind-01,blind,var/validation/blind-01.json,,,industry-neutral sample
```

`role` must be one of `positive`, `control`, or `blind`.

## Execution

```text
predeclare labels / controls
  -> collect bounded paired transcripts
  -> run cache-only matched current/baseline experiments
  -> freeze result JSON
  -> evaluate manifest with ibs-phase1-validate
  -> inspect blind results only after freezing
  -> decide whether Phase 1 is viable for Phase 2
```

The validation evaluator never changes scanner vocabulary, trigger thresholds, discovery scores, or result files.

## Phase 2 gate

Proceed to public/physical validation and triangulation only after:

1. the labeled validation manifest passes the declared recall/false-positive gates,
2. at least one blind cohort produces a plausible nontrivial ranking without theme preselection,
3. evidence concentration and missing-data diagnostics do not explain the result,
4. the discovery result is reproducible from cached data.

Until then, Repo B remains untouched and no discovery result is treated as an investment candidate.
