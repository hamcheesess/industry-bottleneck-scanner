# Transcript source strategy — retained operating-evidence subsystem

Status: **REUSE / NOT TOP-LEVEL DISCOVERY STRATEGY**.

The canonical architecture is [`current_roadmap.md`](current_roadmap.md). This document defines how earnings-call transcripts remain usable inside the new source-agnostic operating-evidence layer.

## Current role

Earnings-call transcripts are valuable because prepared remarks and management Q&A contain operational language about demand, backlog, lead times, capacity, qualification barriers, pricing, and inability to meet demand.

They are no longer required to be the primary or complete discovery source.

```text
transcript available
  -> TranscriptSource adapter
  -> normalized EarningsCallTranscript
  -> local cache
  -> turn normalization
  -> prepared / Q&A provenance
  -> existing deterministic scanner
  -> AtomicSignal
  -> optional comparable-window acceleration
  -> operating support for Causal Diagnosis / Industry State
```

A missing transcript remains explicit source unavailability. It is not a negative operating signal and does not block the whole market-triggered discovery pipeline.

## Broader operating-evidence sources

Future source-agnostic ingestion should also normalize usable public text from:

- earnings releases,
- 8-K / 10-Q / 10-K filings,
- investor presentations,
- customer / supplier / competitor disclosures.

When a document is issuer operating language, prefer normalization into the existing `SourceDocument` contract so the current scanner can produce `AtomicSignal` without a parallel extraction system.

Physical/industry statistics that do not fit issuer-language semantics should become `CausalEvidence` or industry-state evidence instead of being forced into `AtomicSignal`.

## Provider boundary

Provider-specific retrieval stays below normalization.

```text
provider transport
  -> normalized transcript/document contract
  -> cache / provenance
  -> extraction
  -> causal/state layers
```

Active causal/state modules must not import Alpha Vantage, Quartr, or another provider directly.

## Alpha Vantage status

Alpha Vantage remains a usable optional transcript provider and the source used by frozen validation v1. Its existing adapter/cache logic stays available for bounded collection and regression work.

Collection principles remain:

- cache first,
- explicit request budget,
- rate-limit aware,
- resumable,
- API-key material excluded from provenance URLs,
- no raw full-transcript LLM requirement.

Frozen v1 remains Alpha-Vantage-only and is not retrofitted with new fallback sources.

## Quartr status

The repository contains a synthetic-tested Quartr edited-transcript adapter and pair-coherent fallback resolver from the superseded transcript-v2 design.

Usable Quartr API access is unavailable, so these modules are **PARKED**:

- keep code/tests for audit or possible future optional use;
- do not make active architecture depend on them;
- do not make Quartr availability a phase-readiness gate;
- do not extend transcript-specific `v2_source_provenance.py` into the general source model.

See [`implementation_compatibility.md`](implementation_compatibility.md).

## Fiscal-quarter and timestamp discipline

Explicit issuer fiscal-quarter requests remain necessary for transcript collection. A global calendar-quarter label must not be assumed to mean the same fiscal period for every issuer.

`published_at` must remain a real timezone-aware event timestamp. Fiscal-quarter labels must not be fabricated into event dates.

For the current architecture, document timing has an additional role relative to a later Market Trigger:

- pre-existing operating state,
- since-last-earnings update,
- trigger-era catalyst evidence.

A two-month-old call can therefore be useful pre-news evidence without being treated as the immediate cause of today's market move.

## Transcript structure correctness

The existing quality rules remain active:

- preserve turns and speakers when available;
- preserve prepared-vs-Q&A provenance;
- exclude analyst questions from issuer operating evidence;
- retain management Q&A answers;
- keep direction, negation, and resolution semantics;
- do not treat source-section labels as independent evidence classes.

## Comparable-window acceleration

Matched current-vs-baseline transcript experiments remain a useful optional method for measuring operating-language acceleration when comparable source windows exist.

They are no longer a universal prerequisite for Causal Diagnosis. A future source-agnostic operating-support interface should combine comparable acceleration when available with one-sided recent disclosures, since-last-earnings updates, and source freshness/coverage diagnostics.

## Cost and safety

- no universe-scale transcript backfill is required for market discovery;
- cached transcripts should be reused indefinitely subject to provenance correctness;
- provider gaps must not trigger retry loops or cohort mutation;
- cheap deterministic extraction stays local-first;
- model calls, if later used, operate only on already-filtered research material and cannot by themselves approve causal edges or industry state.
