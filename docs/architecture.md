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

## Two-engine boundary

### Repo A: industry-bottleneck-scanner

Discovery engine only.

```text
Documents
  -> signal extraction
  -> atomic signals
  -> company/industry aggregation
  -> signal acceleration
  -> cluster trigger
  -> later: public-data validation
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

Repo A must not calculate DCF or produce final investment reports. Repo B should not rediscover or rescore industries.

## Phase 1 boundary

Phase 1 is intentionally narrow and local-first.

### Inputs

A normalized `SourceDocument` record supplied by fixtures or future ingestion adapters.

### Processing

1. match industry-independent phenomenon vocabulary
2. normalize matches into `AtomicSignal`
3. reject/discount obvious negation and resolved conditions
4. aggregate by company and classification bucket
5. compare current vs baseline windows
6. calculate signal acceleration
7. emit research-trigger clusters

### Outputs

- atomic signal JSONL
- aggregate snapshots
- research-trigger cluster JSON

### Explicitly out of scope for Phase 1

- live SEC crawling
- paid transcript integrations
- LLM/API extraction
- physical KPI integrations
- value-chain mapping
- candidate-company ranking
- cross-repository handoff

## Design principles

### Phenomenon-first

Industry names are metadata for aggregation, not the initial query.

### Independent-company breadth over mention count

Ten separate companies mentioning a constraint is stronger evidence than one company repeating it ten times.

### Direction matters

`lead times increased` and `lead times normalized` cannot score the same way.

### Evidence provenance is mandatory

Every atomic signal keeps the source document, observed text span, dates, and extraction method.

### Local-first cost control

Keyword/regex matching, counting, aggregation, acceleration, and thresholding should be deterministic Python by default. Expensive model calls are reserved for later triggered research.

### No silent investment inference

Phase 1 detects operational anomalies; it does not declare an industry attractive or a stock investable.
