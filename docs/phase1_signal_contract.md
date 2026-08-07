# Phase 1 Signal Contract

## Logical scanner categories

The scanner has four logical categories. They are classification dimensions, not necessarily four separate runtime passes.

The detailed metric taxonomy is defined in [`signal_taxonomy.md`](signal_taxonomy.md).

### Capex

Detect changes in expected investment or concrete capacity expansion, not merely high absolute capex.

Primary metrics:

- `capex_revision_up`
- `capex_revision_down`
- `capacity_expansion`

### Demand

Detect order intake and forward-demand strength.

Primary metrics:

- `backlog_strength`
- `backlog_weakness`
- `bookings_strength`
- `book_to_bill_above_one`
- `forward_capacity_commitment`

### Scarcity

Detect inability of supply to satisfy demand or structural barriers to rapid supply response.

Primary metrics:

- `lead_time_pressure`
- `capacity_constraint`
- `supply_tightness`
- `allocation`
- `sold_out_capacity`
- `qualification_barrier`

### Pricing

Detect whether scarcity/demand is translating into economic capture.

Primary metrics:

- `pricing_power`
- `contract_repricing`
- `margin_from_pricing`
- `pricing_weakness`

## AtomicSignal

Every accepted observation is normalized to one atomic record and may be emitted as JSONL for later audit and aggregation.

```json
{
  "signal_id": "stable-id",
  "scanner": "capex|demand|scarcity|pricing",
  "metric": "taxonomy metric",
  "direction": "strengthening|weakening|stable|unclear",
  "magnitude": "low|medium|high|unknown",
  "company_id": "issuer identifier",
  "ticker": "optional ticker",
  "classification": {
    "sector": "optional",
    "industry": "optional",
    "subindustry": "optional"
  },
  "subject": "product/capacity/segment referred to by the evidence, when defensibly extracted",
  "document_id": "source identifier",
  "document_type": "earnings_call_turn|10-K|10-Q|8-K|release|other",
  "published_at": "ISO-8601 date/time",
  "source_url": "optional",
  "evidence_text": "minimal supporting span",
  "negated": false,
  "resolved": false,
  "extraction_method": "keyword|regex|semantic_local|combined",
  "confidence": 0.0,
  "matched_phrase": "exact deterministic phrase when applicable",
  "comparison_basis": "prior_period|prior_guidance_or_plan|threshold|forward_commitment|unspecified",
  "source_section": "prepared|qa|optional",
  "speaker": "optional transcript speaker",
  "speaker_title": "optional transcript speaker title"
}
```

## Important semantic rules

### Negation and resolution

Statements such as `we are no longer capacity constrained` must not be counted as active scarcity. A strengthening phrase followed by explicit normalization can be retained as counter-evidence with `resolved=true` and `direction=weakening`.

### Direction

Strengthening and weakening observations remain distinct. An explicit weakening taxonomy pattern such as `pricing declined` is not automatically labeled as a resolved historical constraint.

### Subject is not speaker

`subject` describes the constrained product, capacity node, segment, or other economic object. It must never be populated with the transcript speaker. Speaker provenance belongs in `speaker` and `speaker_title`. Phase 1 permits `subject=null` until a defensible subject extractor exists.

### Source section

Earnings-call turns retain whether they came from prepared remarks or Q&A. Q&A is analytically useful but does not count as an independent source merely because it is a different section of the same call.

### Comparison preservation

When the evidence supports it, retain whether the signal is a prior-period change, guidance/plan revision, threshold observation, or forward commitment. Do not invent a comparison when the sentence does not provide one.

## Retrieval and adjudication

The local retrieval stack is recall-oriented:

```text
keyword / phrase
+ flexible regex
+ optional local semantic retrieval
    -> merged RetrievalCandidate
    -> deterministic adjudication
    -> accepted AtomicSignal OR review queue
```

Keyword/regex-backed candidates are auditable deterministic evidence. Medium-confidence semantic-only candidates stay outside aggregation in a persistent review queue. Repeated semantic-only language across multiple independent issuers may become a **vocabulary-development candidate**, but it never becomes a production signal or vocabulary rule automatically.

## Aggregation

Phase 1 defaults to **industry-level** aggregation. Sector and subindustry views are configurable drill-down levels, but silently choosing the finest available classification would fragment related issuers and suppress cross-company breadth.

For each aggregation bucket and time window record:

- distinct companies with active strengthening signals
- distinct active documents
- scanner-category breadth
- metric breadth
- source/document-type breadth
- prepared-vs-Q&A evidence counts
- strengthening signal count
- weakening/resolution counter-evidence count
- confidence mean
- confidence-weighted active signal count

Repeated phrases from one issuer must not be treated as equivalent to broad confirmation across independent companies.

## Signal acceleration

Phase 1 keeps trigger components explicit rather than hiding them behind one opaque score.

Components include:

- `breadth_current`: distinct companies with active strengthening evidence
- `breadth_baseline`: comparable matched-cohort breadth
- `breadth_change`: current minus baseline
- `breadth_ratio`: guarded current/baseline ratio
- `category_breadth`: number of Capex/Demand/Scarcity/Pricing categories active
- `metric_breadth`: number of distinct metrics active
- `source_type_breadth`: number of distinct source/document types
- `core_pair_present`: whether both Demand and Scarcity are active
- `confirmation_count`: number of Capex/Pricing confirmation categories active
- `confidence_mean`

Current and baseline windows must use the same eligible issuer cohort. Missing provider coverage must not masquerade as signal acceleration.

## Research trigger hierarchy

### Triggered

Default Phase 1 logic:

```text
minimum independent companies
AND positive breadth acceleration
AND Demand + Scarcity core pair
AND minimum category breadth
AND minimum confidence
```

### Confirmed

A triggered cluster becomes confirmed when at least one configurable confirmation category is present. The default confirmation set is Capex and Pricing.

```text
Demand + Scarcity acceleration
    -> research trigger
    -> Capex and/or Pricing confirmation
    -> stronger research candidate
```

Phase 1 must emit the AtomicSignal evidence, quality diagnostics, and every trigger component so the result remains inspectable without an LLM call.
