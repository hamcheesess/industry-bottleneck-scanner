# Transcript Source Strategy

## Decision

Earnings-call transcripts are the primary Phase-1 discovery source because prepared remarks and especially Q&A contain operational language about lead times, capacity, reservations, qualification barriers, pricing, and inability to meet demand. SEC filings and earnings releases remain important validation/fallback sources.

## Source priority

1. earnings-call transcript
2. earnings release / investor-relations material
3. SEC 10-Q / 10-K / 8-K
4. later fallback: first-party webcast/audio converted to text when permitted

## Adapter boundary

Provider-specific retrieval is hidden behind `TranscriptSource`.

```text
explicit ticker + fiscal-quarter request
  -> TranscriptSource adapter
  -> normalized EarningsCallTranscript
  -> local cache
  -> turn normalization
  -> prepared / Q&A section inference
  -> local candidate retrieval
  -> AtomicSignal / review queue
```

Provider adapters only retrieve and normalize transcript data. They never send raw calls to an LLM. The cache stores the normalized transcript contract rather than raw provider responses.

## Alpha Vantage operating status

Alpha Vantage is the provisional primary provider for the Phase-1 pilot. The adapter uses `EARNINGS_CALL_TRANSCRIPT` with explicit `symbol` and issuer-specific fiscal `quarter` values. The provider URL containing the API key is never stored as signal provenance.

A real five-company probe succeeded 5/5 after enforcing the provider's observed one-request-per-second constraint. This establishes endpoint viability, not Russell 3000 coverage.

Collection therefore remains:

- cache first
- explicit request-list based
- request-budget capped
- rate-limit aware
- resumable across runs
- free of OpenAI/GPT calls

## Fiscal-quarter discipline

A global calendar-quarter label must not be assumed to mean the same fiscal period for every issuer. Collection accepts explicit `(ticker, quarter)` pairs, and matched experiments use dated company-period metadata.

The fiscal-quarter label is never converted into an earnings-call date. `published_at` must be an explicit timezone-aware event timestamp. The metadata contract can retain the public URL used to establish that timestamp.

## Transcript structure quality

A provider is useful only if its normalized transcript structure is usable. The pilot measures:

- turn count
- speaker-label coverage
- title/role-label coverage
- whether Q&A can be detected
- prepared-vs-Q&A turn counts

Q&A inference is conservative: an explicit Q&A marker or analyst turn starts the Q&A section, and subsequent turns remain in that section. Section labels are provenance; they do not create additional source independence.

## Bounded matched pilot

Before universe-scale collection, the repository runs a matched current-vs-baseline pilot over explicit issuer/quarter pairs. A pilot is ready for signal-acceleration analysis only when enough issuers have both periods cached. Provider gaps and rate-limited pairs remain unresolved rather than being treated as negative evidence.

The current pilot manifest focuses on power/electrical infrastructure issuers with one control company and consecutive fiscal quarters. The experiment defaults to industry-level aggregation so distinct subindustry labels do not fragment the cross-company breadth test.

## Cost and safety rules

- every live collection has an explicit provider-request cap
- cached calls consume no provider budget
- rate-limit responses stop the run rather than triggering retry storms
- no universe-scale backfill occurs before bounded pilot validation
- no OpenAI/GPT call is part of transcript acquisition or Phase-1 scanning
- raw full transcripts are never sent to an LLM by default
- future model use, if any, is limited to ambiguous retrieved passages or already-triggered clusters
