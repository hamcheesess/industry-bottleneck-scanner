# Transcript Source Strategy

## Decision

Earnings-call transcripts are a first-class discovery source and should be evaluated before SEC filings become the primary ingestion path.

The discovery engine should prefer operating language from management commentary and Q&A, while SEC filings remain validation and fallback sources.

## Source priority

1. earnings-call transcript
2. earnings release / investor-relations material
3. SEC 10-Q / 10-K / 8-K
4. later fallback: first-party webcast/audio converted to text when permitted

## Architecture

Provider-specific retrieval is hidden behind `TranscriptSource`.

```text
Russell 3000 snapshot
  -> TranscriptSource adapter
  -> normalized EarningsCallTranscript
  -> high-recall passage retrieval
  -> AtomicSignal
  -> cross-company aggregation
```

Provider adapters must only retrieve and normalize transcript data. They must never send raw calls to an LLM.

## Alpha Vantage pilot

The official Alpha Vantage API currently documents `EARNINGS_CALL_TRANSCRIPT` with required `symbol`, `quarter` (`YYYYQ#`), and `apikey` parameters, with history documented from 2010Q1 onward.

The initial adapter is intentionally dependency-light and transport-injectable so unit tests perform no network calls.

## Coverage experiment before adoption

Do not assume Russell 3000 coverage from marketing or documentation. Measure it.

Start with a bounded 20-50 company sample that deliberately spans:

- mega cap / large cap
- mid cap
- small cap
- NYSE and Nasdaq
- industrials
- technology
- consumer
- energy/materials
- healthcare
- financials

For one recent completed fiscal quarter record, per ticker:

- transcript available / missing
- number of speaker turns
- whether management speakers appear
- whether analyst/Q&A turns appear
- provider error or rate-limit response

Acceptance questions:

1. Is recent-quarter availability high enough to serve as a primary source?
2. Does coverage degrade materially for Russell 3000 small caps?
3. Are speaker turns usable for management-vs-analyst separation?
4. What request limits and commercial/licensing constraints apply?
5. Is a second provider required as fallback?

## Cost safety rules

- coverage probes must have an explicit request cap
- no universe-scale backfill until a small sample is reviewed
- no OpenAI/GPT call is part of transcript acquisition
- raw transcript text must not be sent to an LLM by default
- later model use, if any, is restricted to already-retrieved ambiguous passages or triggered clusters
