# Historical transcript-validation v2 draft — superseded

Status: **SUPERSEDED AS AN ACTIVE ROADMAP**.

This file records the abandoned design direction that followed frozen transcript validation v1. It is retained so the repository has an explicit audit trail rather than silently erasing the Quartr-centered work.

The active system roadmap is now [`current_roadmap.md`](current_roadmap.md), with implementation compatibility rules in [`implementation_compatibility.md`](implementation_compatibility.md).

## Why this draft is no longer active

The old v2 design assumed that the next discovery architecture should solve transcript completeness using a predeclared multi-provider transcript fallback hierarchy:

```text
Alpha Vantage transcript
  -> missing
  -> Quartr edited transcript
```

That direction is no longer appropriate for the system because:

1. usable Quartr API access is unavailable;
2. complete transcript coverage is not actually required for the investment-discovery objective;
3. transcripts are now one operating-evidence source among earnings releases, SEC disclosures, presentations, customer/supplier evidence, and public physical data;
4. the top-level architecture is market-triggered causal expansion rather than transcript-first broad discovery.

No active module may treat Quartr availability or complete transcript pairs as a system-wide discovery gate.

## What is still retained from the old draft

The old work produced useful subsystem principles that remain valid:

- source coverage must be distinguished from negative operating evidence;
- provider/document provenance must remain explicit;
- missing documents must never silently shrink a frozen validation cohort;
- current/baseline comparison must avoid source-format artifacts when used;
- analyst questions must not be promoted as issuer operating evidence;
- extraction correctness is separately testable from acceleration correctness;
- look-ahead-safe `as_of` cutoffs are mandatory for historical replay;
- validation thresholds and cohorts must not be rewritten after outcomes are visible.

The existing Alpha Vantage adapter/cache, transcript scanner, Quartr adapter, fallback resolver, and Quartr-era source-provenance tests may remain in the repository. Their status is defined in [`implementation_compatibility.md`](implementation_compatibility.md): Alpha Vantage/transcript scanning is **REUSE**, while Quartr/fallback-v2 code is **PARKED**.

## Frozen v1 remains frozen

This supersession does not rewrite frozen validation v1. Its source-coverage-limited result remains the historical record of the Alpha-Vantage-only transcript experiment.

## Replacement validation direction

The active system will eventually validate separate layers:

1. market-trigger quality;
2. operating-evidence extraction correctness;
3. causal-edge correctness;
4. pre-shock industry-state correctness and timestamp safety;
5. independent demand-root convergence;
6. pre-news node ranking;
7. company exposure mapping;
8. end-to-end historical replay without post-event leakage.

Old transcript extraction/control cases may be reused where they test a still-active subsystem, but this document is not executable and cannot make the current architecture ready for later phases.
