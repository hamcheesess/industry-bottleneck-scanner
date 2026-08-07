# Architecture

## Goal

Discover investable industry bottlenecks inductively from changing operating language and operating data across many companies.

The system should answer, in order:

1. What phenomenon is accelerating?
2. Which companies and clusters show it repeatedly?
3. Is the signal independently corroborated?
4. What industry/value-chain node explains the cluster?
5. Where is supply elasticity lowest?
6. Who captures the economics?
7. Which listed companies should be handed to downstream underwriting?

## Canonical discovery universe

Repo A uses the **Russell 3000 membership universe** as its broad US-listed discovery universe. Membership is represented as a dated snapshot with separate issuer and security identities rather than a hard-coded constituent list.

```text
Russell 3000 membership snapshot
  -> normalize tickers / share classes
  -> preserve issuer_id + security_id
  -> resolve source identities such as SEC CIK
  -> incremental disclosure collection
```

Unresolved identifiers stay explicit rather than being silently dropped.

## Two-engine boundary

### Repo A: industry-bottleneck-scanner

Discovery engine only.

```text
Russell 3000 universe
  -> issuer/security registry
  -> transcript/disclosure sources
  -> local phenomenon retrieval
  -> AtomicSignal
  -> cross-company industry aggregation
  -> signal acceleration
  -> research trigger
  -> later: physical/public-data validation
  -> later: customer/supplier triangulation
  -> later: industry/value-chain mapping
  -> later: bottleneck/economic-capture analysis
  -> later: candidate manifest
```

### Repo B: investment-research-automation

Underwriting engine only.

```text
Candidate manifest
  -> local financial gate
  -> financial risk filter
  -> ranked queue
  -> company deep research
  -> DCF
  -> final company report
```

Repo A must not calculate DCF or produce final investment reports. Repo B should not rediscover industries already surfaced upstream.

## Phase 1: discovery proof

Phase 1 is intentionally local-first and stops at abnormal industry-cluster discovery. It does not yet perform value-chain mapping or candidate-company ranking.

### Primary source path

Earnings calls are the primary Phase-1 operating-language source, with earnings releases and SEC disclosures available as later corroborating/fallback adapters.

```text
explicit issuer + fiscal-quarter request
  -> provider adapter
  -> normalized transcript cache
  -> turn-level documents
  -> prepared / Q&A provenance
  -> lexical + regex retrieval
  -> optional local semantic retrieval
  -> deterministic adjudication
  -> AtomicSignal OR semantic review queue
```

Raw transcripts are not sent to an LLM.

### Comparable-window experiment

Signal acceleration must compare like with like:

```text
current metadata manifest -----+
                               +-> matched issuer cohort
baseline metadata manifest ----+
                               -> require cached transcript in both windows
                               -> scan both windows
                               -> industry aggregation
                               -> breadth acceleration
```

Provider coverage gaps are not negative signals and cannot inflate apparent acceleration.

### Aggregation level

The Phase-1 default is **industry-level** aggregation. Sector and subindustry are explicit configurable views. The system must not silently use the finest available classification because that can fragment related issuers and destroy the independent-company breadth signal.

### Retrieval learning loop

Medium-confidence semantic-only candidates remain outside production aggregation. Pending review candidates can be clustered locally across independent issuers to surface repeated novel management language.

```text
semantic-only review queue
  -> repeated cross-company expression cluster
  -> vocabulary-development candidate
  -> review
  -> optional future taxonomy/vocabulary update
```

There is no automatic feedback from an embedding cluster into production vocabulary or accepted signals.

### Quality diagnostics

Phase-1 experiment artifacts expose data-quality checks alongside research triggers, including:

- matched/eligible issuer counts
- missing and unresolved transcript pairs
- speaker/title label coverage
- Q&A detection rate
- unclassified-signal count
- issuer concentration of active signals
- metric/extraction-method distributions
- prepared-vs-Q&A signal counts

### Outputs

- immutable universe snapshot contract
- normalized cached transcripts
- persistent semantic review queue
- current/baseline `AtomicSignal` JSONL
- aggregate snapshots
- acceleration/trigger JSON
- transcript/provider quality diagnostics
- novel-language review candidates

### Explicitly out of scope for Phase 1

- live acquisition of an unlicensed Russell constituent list
- universe-scale transcript backfill before pilot validation
- raw-transcript LLM analysis
- physical KPI integrations
- value-chain mapping
- bottleneck/economic-capture scoring
- candidate-company ranking
- Repo B handoff

## Current bounded pilot

The repository contains a matched power/electrical-infrastructure pilot using consecutive issuer-specific fiscal quarters and explicit event timestamps. The pilot includes several Electrical Equipment issuers plus an Electronic Components control. It is deliberately small enough to stay within a bounded provider-request budget and large enough to test independent-company industry breadth.

`ibs-phase1-pilot` runs collection, cache validation, transcript-structure diagnostics, matched scanning, industry aggregation, acceleration, artifact persistence, and novel-language review in one bounded workflow.

## Design principles

### Phenomenon-first

Industry names are metadata for aggregation, not the initial search query.

### Broad discovery before financial filtering

Financial quality filters belong downstream so structurally important bottleneck beneficiaries are not excluded before phenomenon discovery.

### Independent-company breadth over mention count

Ten independent issuers mentioning a constraint is stronger evidence than one issuer repeating it ten times.

### Direction and counter-evidence matter

`lead times increased` and `lead times normalized` cannot score the same way. Weakening/resolution evidence remains visible but does not inflate active breadth.

### Evidence provenance is mandatory

Every accepted signal keeps source identity, evidence text, real timestamp, extraction method, transcript section, and speaker metadata when available. Economic `subject` is separate from transcript speaker identity.

### Local-first cost control

Keyword/regex matching, local embeddings, adjudication, aggregation, acceleration, diagnostics, and thresholding run locally by default. Paid model calls are reserved for later ambiguous or already-triggered research stages.

### No silent investment inference

Phase 1 detects operational anomalies; it does not declare an industry attractive or a stock investable.
