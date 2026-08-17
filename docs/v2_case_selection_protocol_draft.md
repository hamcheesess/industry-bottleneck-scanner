# V2 case selection protocol — draft

Status: **draft only; not frozen**.

V2 cases must be chosen from external event timelines and source-backed operating evidence, not from scanner outcomes. Source availability may be checked before the final freeze, but scanner results must remain unseen during case selection.

## Two-stage selection

### Stage A — outcome-blind candidate pool

Build candidate cases from public evidence only. For every candidate, record:

- phenomenon being tested,
- issuer/industry scope,
- candidate current window,
- candidate baseline window when applicable,
- external evidence URLs and dates,
- why the current evidence supports the broad phenomenon,
- why the baseline is plausibly quieter for acceleration tests.

Do not run the scanner to decide which candidates survive.

### Stage B — source-feasibility screen

Before freezing the final V2 manifest, test whether every required issuer-window can be represented under the predeclared transcript hierarchy.

A case may be rejected at this stage for source infeasibility only if:

- rejection occurs before scanner output is inspected,
- the reason is recorded as source coverage,
- replacement comes from the predeclared candidate pool or another candidate selected under the same outcome-blind rules.

This prevents the V1 failure mode in which a frozen case becomes impossible to score while also preventing post-outcome cohort repair.

## Extraction cases

Draft target: 6 cases.

Each extraction case should test source-backed operating evidence in the current window only. Ground truth must support the broad phenomenon or explicitly named metric. A case must not require a narrow taxonomy term that the external evidence itself does not establish.

Preferred diversity:

- multiple sectors/industries,
- more than one signal family among Capex, Demand, Scarcity, Pricing,
- both prepared remarks and management Q&A evidence when available,
- no analyst-question evidence as ground truth.

## Acceleration-positive pairs

Draft target: 6 current/baseline pairs.

The external event timeline must support a meaningful strengthening from baseline to current. A pair is not eligible merely because the phenomenon existed in both windows.

Before freeze, document:

- evidence that baseline is materially quieter or earlier-stage,
- evidence that current shows stronger operating conditions,
- comparable issuer cohort,
- expected broad core-category behavior.

Exact taxonomy-metric recovery belongs to extraction validation and is not required for an acceleration-positive label unless independently source-backed.

## Controls

Draft target: 8 controls.

Controls should be matched to positive issuer families/sectors where practical and selected from plausibly quiet, pre-event, or non-accelerating windows using external evidence.

A control must not be selected only because the current scanner happens not to trigger on it.

After execution, any triggered control is reviewed and classified as:

- scanner correctness defect,
- ambiguous/precursor real signal,
- control-label weakness.

Only a general correctness defect reproduced independently of the labeled outcome may change scanner code during the frozen run.

## Blind cohort

The blind cohort remains deterministic and outcome-blind. Cohort construction, windows, source policy, aggregation level, and ranking rubric are frozen before scanning.

No known-positive theme is injected into the blind cohort as a requirement.

## Freeze checklist

The executable V2 manifest should not be frozen until all of these are complete:

- transcript source hierarchy is accessible and entitlement-verified,
- source-feasibility screen is complete without scanner-output inspection,
- exact extraction/acceleration/control cases and evidence timelines are recorded,
- blind cohort and ranking rubric are fixed,
- integer gates are fixed,
- provider-mix provenance/fingerprint path is wired,
- no unresolved scanner correctness defect remains.

Frozen V1 remains unchanged regardless of the V2 case set.
