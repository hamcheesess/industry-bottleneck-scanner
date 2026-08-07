# Phase 1 Signal Contract

## Logical scanner categories

The scanner has four logical categories. They are classification buckets, not necessarily four separate runtime passes.

### Capex

Detect changes in expected investment or capacity expansion, not merely high absolute capex.

Representative concepts:

- capex guidance raised/lowered
- capital plan increased/decreased
- capacity expansion
- greenfield/brownfield project
- new facility / production line
- equipment investment

### Demand

Detect order intake and forward-demand strength.

Representative concepts:

- backlog
- bookings
- book-to-bill
- record orders
- customer commitments
- reservations of future capacity

### Scarcity

Detect inability of supply to satisfy demand or long replacement/qualification cycles.

Representative concepts:

- lead times
- constrained capacity
- shortage
- allocation
- sold out
- limited availability
- unable to meet demand
- qualification duration

### Pricing

Detect whether scarcity/demand is translating into economics.

Representative concepts:

- pricing remains strong
- price increase
- favorable price/cost
- margin expansion attributed to price
- contract repricing
- take-or-pay / reservation economics

## AtomicSignal

Every extracted observation is normalized to one atomic record.

Required fields:

```json
{
  "signal_id": "stable-id",
  "scanner": "capex|demand|scarcity|pricing",
  "metric": "lead_time|backlog|book_to_bill|capacity_expansion|pricing|...",
  "direction": "strengthening|weakening|stable|unclear",
  "magnitude": "low|medium|high|unknown",
  "company_id": "issuer identifier",
  "ticker": "optional ticker",
  "classification": {
    "sector": "optional",
    "industry": "optional",
    "subindustry": "optional"
  },
  "subject": "what product/capacity/segment the statement refers to",
  "document": {
    "document_id": "source identifier",
    "document_type": "10-K|10-Q|8-K|transcript|release|other",
    "published_at": "ISO-8601 date/time",
    "source_url": "optional"
  },
  "evidence_text": "minimal supporting span",
  "negated": false,
  "resolved": false,
  "extraction_method": "keyword|regex|rule|model",
  "confidence": 0.0
}
```

## Important semantic rules

### Negation

Statements such as `we are no longer capacity constrained` must not be counted as active scarcity.

### Direction

`lead times increased` is strengthening scarcity.
`lead times declined` is weakening scarcity.

### Resolution

A historical constraint followed by explicit normalization should be marked `resolved=true` when the text supports it.

### Subject preservation

Do not collapse `transformers`, `switchgear`, and `cables` into one generic company-level scarcity signal if the text identifies the constrained item.

## Aggregation

Primary aggregation should emphasize independent issuers.

For each classification bucket and time window record:

- distinct companies with active signals
- distinct documents
- weighted signal count
- scanner-category breadth
- direction balance
- median/mean confidence
- current-window vs baseline-window company breadth

## Signal acceleration

Phase 1 should keep the scoring formula configurable. The initial implementation should expose components rather than hide them behind one opaque score.

Recommended components:

- `breadth_current`: distinct companies with strengthening active signal
- `breadth_baseline`: comparable baseline breadth
- `breadth_change`: current minus baseline
- `breadth_ratio`: guarded current/baseline ratio
- `category_breadth`: number of Capex/Demand/Scarcity/Pricing categories active
- `source_breadth`: distinct source/document types
- `confidence_mean`

## Research trigger

A cluster becomes a research candidate only when configurable minimums are met. Initial defaults should be conservative and easy to change in config.

Illustrative trigger logic:

```text
minimum independent companies
AND positive breadth acceleration
AND at least two scanner categories
AND minimum confidence
```

A stronger trigger can require Demand + Scarcity, with Pricing or Capex acting as confirmation.

Phase 1 must emit the evidence and score components so a human can inspect why the trigger fired.
